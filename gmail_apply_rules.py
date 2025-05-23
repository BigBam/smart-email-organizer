import os
import datetime
from datetime import UTC
from dateutil.relativedelta import relativedelta
import google.auth
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import logging
import threading
import time
import json
from typing import List, Dict, Any, Optional, Callable

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Changed from DEBUG to INFO level
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gmail_rules.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

# Global control events
pause_event = threading.Event()
stop_event = threading.Event()

class GmailRule:
    def __init__(self, name: str, condition: Callable[[Dict[str, Any]], bool], action: Callable[[Dict[str, Any], Any], None]):
        self.name = name
        self.condition = condition
        self.action = action

def set_pause(pause: bool) -> None:
    """Set or clear the pause event."""
    if pause:
        pause_event.set()
        logger.info("Processing paused")
    else:
        pause_event.clear()
        logger.info("Processing resumed")

def set_stop() -> None:
    """Set the stop event."""
    stop_event.set()
    logger.info("Processing stopped by user")

def check_pause(log_func=None) -> None:
    """Check if processing should be paused or stopped."""
    if stop_event.is_set():
        raise Exception("Processing stopped by user")
        
    if pause_event.is_set():
        if log_func:
            log_func("Processing paused...")
        while pause_event.is_set() and not stop_event.is_set():
            time.sleep(0.1)
        if not stop_event.is_set():
            if log_func:
                log_func("Processing resumed...")

def authenticate_gmail():
    """Authenticate with Gmail API."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

def get_all_messages(service, query: Optional[str] = None, log_func=None) -> List[Dict[str, Any]]:
    """Fetch all messages from Gmail."""
    if log_func is None:
        log_func = logger.info
        
    messages = []
    page_token = None
    page_count = 0
    MAX_MESSAGES = 100000
    
    while True:
        check_pause(log_func)  # Check for pause
        try:
            if len(messages) >= MAX_MESSAGES:
                log_func(f"Reached maximum message limit of {MAX_MESSAGES}")
                break

            response = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=500,
                pageToken=page_token
            ).execute()
            
            if 'messages' in response:
                messages.extend(response['messages'])
                page_count += 1
                log_func(f"Fetched {len(messages)} messages (page {page_count})")
                check_pause(log_func)  # Check for pause after each page
            
            page_token = response.get('nextPageToken')
            if not page_token:
                break
                
        except Exception as e:
            log_func(f'Error fetching messages: {e}')
            break
    
    return messages

def get_or_create_label(service, label_name: str) -> str:
    """Get or create a Gmail label."""
    labels = service.users().labels().list(userId='me').execute().get('labels', [])
    label_id = next((label['id'] for label in labels if label['name'] == label_name), None)

    if not label_id:
        label_body = {
            'name': label_name,
            'labelListVisibility': 'labelShow',
            'messageListVisibility': 'show'
        }
        created_label = service.users().labels().create(userId='me', body=label_body).execute()
        label_id = created_label['id']
        logger.info(f'Created new label: {label_name}')

    return label_id

def apply_rules(service, rules: List[GmailRule], log_func=None) -> None:
    """Apply a list of rules to all messages."""
    # Reset stop event at the start of processing
    stop_event.clear()
    
    if log_func is None:
        log_func = logger.info
    
    log_func("Starting rule application process...")
    log_func(f"Total rules to apply: {len(rules)}")
    
    # Fetch all messages
    log_func("Fetching all messages...")
    all_messages = get_all_messages(service, log_func=log_func)
    total_count = len(all_messages)
    log_func(f"Total messages to process: {total_count}")
    
    # Process messages
    processed_count = 0
    rules_applied = {rule.name: 0 for rule in rules}
    
    for msg in all_messages:
        check_pause(log_func)  # Check for pause
        processed_count += 1
        
        if processed_count % 100 == 0:
            log_func(f"Processed {processed_count}/{total_count} messages...")
            for rule_name, count in rules_applied.items():
                log_func(f"Rule '{rule_name}' applied {count} times")
            check_pause(log_func)  # Check for pause after each batch
            
        try:
            # Get full message with headers
            full_message = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='full'
            ).execute()
            
            logger.debug(f"Processing message {msg['id']}")
            logger.debug(f"Message headers: {json.dumps(full_message.get('payload', {}).get('headers', []), indent=2)}")
            
            # Apply each rule
            for rule in rules:
                if rule.condition(full_message):
                    rule.action(full_message, service)
                    rules_applied[rule.name] += 1
                    log_func(f"Applied rule '{rule.name}' to message {msg['id']}")
                    
        except Exception as e:
            log_func(f"Error processing message {msg['id']}: {str(e)}")
            continue
    
    # Log final statistics
    log_func("Rule application complete!")
    log_func(f"Total messages processed: {processed_count}")
    for rule_name, count in rules_applied.items():
        log_func(f"Rule '{rule_name}' was applied {count} times")

def load_rules_from_json() -> List[GmailRule]:
    """Load rules from rules.json file."""
    try:
        with open('rules.json', 'r') as f:
            rules_data = json.load(f)
        
        rules = []
        for rule_data in rules_data:
            # Create condition function based on rule data
            def create_condition(rule):
                def condition(msg):
                    try:
                        # Get message metadata
                        headers = []
                        if 'payload' in msg:
                            headers = msg['payload'].get('headers', [])
                        elif 'headers' in msg:
                            headers = msg['headers']
                            
                        # Get the header value based on the condition field
                        header_value = next((h['value'] for h in headers if h['name'].lower() == rule['condition_field'].lower()), '')
                        logger.debug(f"Message {msg.get('id', 'unknown')} - Found {rule['condition_field']}: {header_value}")
                        
                        if rule['condition_operator'] == 'contains':
                            result = rule['condition_value'].lower() in header_value.lower()
                            logger.debug(f"Message {msg.get('id', 'unknown')} - Rule check: '{rule['condition_value']}' in '{header_value}' = {result}")
                            return result
                        elif rule['condition_operator'] == 'equals':
                            result = rule['condition_value'].lower() == header_value.lower()
                            logger.debug(f"Message {msg.get('id', 'unknown')} - Rule check: '{rule['condition_value']}' equals '{header_value}' = {result}")
                            return result
                        elif rule['condition_operator'] == 'starts with':
                            result = header_value.lower().startswith(rule['condition_value'].lower())
                            logger.debug(f"Message {msg.get('id', 'unknown')} - Rule check: '{header_value}' starts with '{rule['condition_value']}' = {result}")
                            return result
                        elif rule['condition_operator'] == 'ends with':
                            result = header_value.lower().endswith(rule['condition_value'].lower())
                            logger.debug(f"Message {msg.get('id', 'unknown')} - Rule check: '{header_value}' ends with '{rule['condition_value']}' = {result}")
                            return result
                        return False
                    except Exception as e:
                        logger.error(f"Error in condition for message {msg.get('id', 'unknown')}: {e}")
                        return False
                return condition

            # Create action function based on rule data
            def create_action(rule):
                def action(msg, service):
                    try:
                        if rule['action_type'] == 'Label as':
                            # For labeling, we add the label
                            label_id = get_or_create_label(service, rule['action_value'])
                            result = service.users().messages().modify(
                                userId='me',
                                id=msg['id'],
                                body={'addLabelIds': [label_id]}
                            ).execute()
                            logger.info(f"Added label '{rule['action_value']}' to message {msg['id']}")
                            logger.debug(f"Label result: {result}")
                            
                        elif rule['action_type'] == 'Move to':
                            # For moving to categories, we need to handle both Gmail's special category labels
                            # and custom labels
                            category_label = rule['action_value']
                            
                            # First remove from INBOX if it's there
                            current_labels = msg.get('labelIds', [])
                            if 'INBOX' in current_labels:
                                result = service.users().messages().modify(
                                    userId='me',
                                    id=msg['id'],
                                    body={'removeLabelIds': ['INBOX']}
                                ).execute()
                                logger.debug(f"Remove INBOX result: {result}")
                            
                            # Then add the new label
                            if category_label.startswith('CATEGORY_'):
                                # For Gmail's built-in categories
                                result = service.users().messages().modify(
                                    userId='me',
                                    id=msg['id'],
                                    body={'addLabelIds': [category_label]}
                                ).execute()
                                logger.info(f"Moved message {msg['id']} to category {category_label}")
                                logger.debug(f"Add category result: {result}")
                            else:
                                # For custom labels
                                label_id = get_or_create_label(service, category_label)
                                result = service.users().messages().modify(
                                    userId='me',
                                    id=msg['id'],
                                    body={'addLabelIds': [label_id]}
                                ).execute()
                                logger.info(f"Moved message {msg['id']} to label {category_label}")
                                logger.debug(f"Add label result: {result}")
                                
                    except Exception as e:
                        logger.error(f"Error applying action to message {msg['id']}: {e}")
                return action

            rule = GmailRule(
                name=f"{rule_data['condition_field']} {rule_data['condition_operator']} {rule_data['condition_value']}",
                condition=create_condition(rule_data),
                action=create_action(rule_data)
            )
            rules.append(rule)
        
        return rules
    except Exception as e:
        logger.error(f"Error loading rules from JSON: {e}")
        return []

def main():
    """Main function to run the Gmail rules application."""
    try:
        service = authenticate_gmail()
        
        # Load rules from JSON file
        rules = load_rules_from_json()
        if not rules:
            logger.error("No rules loaded from rules.json")
            return
            
        logger.info(f"Loaded {len(rules)} rules from rules.json")
        apply_rules(service, rules)
        
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise

if __name__ == '__main__':
    main() 