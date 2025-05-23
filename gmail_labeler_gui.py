import os
import datetime
from datetime import UTC
from dateutil.relativedelta import relativedelta
import google.auth
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import wx
import threading
import json
import gmail_apply_rules
from gmail_apply_rules import GmailRule

# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

class MainApp(wx.App):
    def OnInit(self):
        self.frame = None
        self.show_auth_frame()
        return True
        
    def show_auth_frame(self):
        if self.frame:
            self.frame.Destroy()
        self.frame = AuthFrame(self)
        self.frame.Show()
        
    def show_main_frame(self, service):
        if self.frame:
            self.frame.Destroy()
        self.frame = MainFrame(self, service)
        self.frame.Show()

class AuthFrame(wx.Frame):
    def __init__(self, app):
        super().__init__(parent=None, title='Gmail Labeler - Authentication', size=(400, 400))
        self.app = app
        
        # Set minimum window size
        self.SetMinSize((300, 400))
        
        self.init_ui()
        
    def init_ui(self):
        panel = wx.Panel(self)
        panel.SetBackgroundColour(wx.Colour(240, 240, 240))  # Light gray background
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        # Welcome text
        welcome_text = wx.StaticText(panel, label="Welcome to Gmail Labeler")
        welcome_text.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        vbox.Add(welcome_text, flag=wx.ALIGN_CENTER | wx.ALL, border=20)
        
        # Add some space
        vbox.AddSpacer(20)
        
        # Auth button with fixed size
        self.auth_button = wx.Button(panel, label="", pos=(0, 0), size=(150, 150))
        self.auth_button.SetFont(wx.Font(32, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.auth_button.SetBackgroundColour(wx.WHITE)  # White background to match label
        self.auth_button.SetForegroundColour(wx.BLACK)  # Black text
        self.auth_button.SetWindowStyle(self.auth_button.GetWindowStyle() | wx.BORDER_SIMPLE)  # Add border
        self.auth_button.SetInitialSize((150, 150))  # Force initial size
        self.auth_button.SetLabel("🔑")  # Set label after button is fully configured
        self.auth_button.Bind(wx.EVT_BUTTON, self.on_authenticate)
        vbox.Add(self.auth_button, 0, wx.ALIGN_CENTER | wx.ALL, 20)
        
        # Countdown text
        self.countdown_text = wx.StaticText(panel, label="", size=(200, 20))
        self.countdown_text.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        self.countdown_text.SetWindowStyle(wx.ALIGN_CENTER)
        vbox.Add(self.countdown_text, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        
        panel.SetSizer(vbox)
        self.Centre()
        
    def on_authenticate(self, event):
        self.auth_button.Disable()
        self.auth_button.SetLabel("⏳")
        
        # Start countdown timer
        self.countdown = 60  # 60 seconds
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.update_countdown, self.timer)
        self.timer.Start(1000)  # Update every second
        
        def auth_thread():
            try:
                service = authenticate_gmail()
                wx.CallAfter(self.on_auth_success, service)
            except Exception as e:
                wx.CallAfter(self.on_auth_error)
        
        threading.Thread(target=auth_thread).start()
        
    def update_countdown(self, event):
        self.countdown -= 1
        if self.countdown <= 0:
            self.timer.Stop()
            self.on_auth_error()
        else:
            self.countdown_text.SetLabel(f"Time remaining: {self.countdown}s")
        
    def on_auth_success(self, service):
        self.timer.Stop()  # Stop the timer
        self.auth_button.SetLabel("✅")
        self.countdown_text.SetLabel("")  # Clear countdown text
        wx.CallLater(500, self.app.show_main_frame, service)  # Short delay to show success
        
    def on_auth_error(self):
        self.timer.Stop()  # Stop the timer
        self.auth_button.SetLabel("❌")
        self.countdown_text.SetLabel("")  # Clear countdown text
        self.auth_button.Enable()

class MainFrame(wx.Frame):
    def __init__(self, app, service):
        super().__init__(parent=None, title='Gmail Labeler', size=(800, 600))
        self.app = app
        self.service = service
        
        # Set minimum window size to ensure buttons fit
        # Width: 3 buttons (150px each) + margins (20px each) + padding (20px each side) = ~550px
        # Height: enough for buttons (150px) + margins + description + status = ~400px
        self.SetMinSize((700, 600))
        
        self.init_ui()
        
    def init_ui(self):
        panel = wx.Panel(self)
        panel.SetBackgroundColour(wx.Colour(240, 240, 240))  # Light gray background
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        # Create notebook (tabs)
        self.notebook = wx.Notebook(panel)
        
        # Operations tab
        operations_panel = wx.Panel(self.notebook)
        operations_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Description text
        description = wx.StaticText(operations_panel, label="Gmail Labeler helps you organize your emails by automatically applying labels based on rules you create.\n\n"
                                                          "Use the Rules tab to create custom rules for labeling emails.\n"
                                                          "Use the Labels tab to manage your Gmail labels.\n\n"
                                                          "Click the power button below to start processing your emails with the current rules.")
        description.Wrap(550)  # Wrap text to fit within minimum window width
        operations_sizer.Add(description, 0, wx.ALL, 20)
        
        # Button container for power and pause buttons
        button_container = wx.BoxSizer(wx.HORIZONTAL)
        
        # Power button
        self.power_button = wx.Button(operations_panel, label="⚡\nStart")
        self.power_button.SetFont(wx.Font(16, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.power_button.SetMinSize((150, 150))  # Square button
        self.power_button.Bind(wx.EVT_BUTTON, self.on_start_processing)
        button_container.Add(self.power_button, 0, wx.ALL, 20)
        
        # Pause button
        self.pause_button = wx.Button(operations_panel, label="⏸\nPause")
        self.pause_button.SetFont(wx.Font(16, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.pause_button.SetMinSize((150, 150))  # Square button
        self.pause_button.Bind(wx.EVT_BUTTON, self.on_pause)
        self.pause_button.Disable()  # Initially disabled
        button_container.Add(self.pause_button, 0, wx.ALL, 20)
        
        # Stop button
        self.stop_button = wx.Button(operations_panel, label="⏹\nStop")
        self.stop_button.SetFont(wx.Font(16, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.stop_button.SetMinSize((150, 150))  # Square button
        self.stop_button.Bind(wx.EVT_BUTTON, self.on_stop)
        self.stop_button.Disable()  # Initially disabled
        button_container.Add(self.stop_button, 0, wx.ALL, 20)
        
        operations_sizer.Add(button_container, 0, wx.ALIGN_CENTER | wx.ALL, 20)
        
        # Status text
        self.status_text = wx.TextCtrl(operations_panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        operations_sizer.Add(self.status_text, 1, wx.EXPAND | wx.ALL, 20)
        
        operations_panel.SetSizer(operations_sizer)
        
        # Rules tab
        self.rules_panel = RulesPanel(self.notebook, self.service)
        
        # Labels tab
        self.labels_panel = LabelsPanel(self.notebook, self.service)
        
        # Settings tab
        self.settings_panel = SettingsPanel(self.notebook, self.service, self.app)
        
        # Add tabs to notebook
        self.notebook.AddPage(operations_panel, "Operations")
        self.notebook.AddPage(self.rules_panel, "Rules")
        self.notebook.AddPage(self.labels_panel, "Labels")
        self.notebook.AddPage(self.settings_panel, "Settings")
        
        vbox.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 5)
        
        panel.SetSizer(vbox)
        self.Centre()
        
    def on_start_processing(self, event):
        self.power_button.Disable()
        self.pause_button.Enable()
        self.stop_button.Enable()
        self.status_text.AppendText("Starting to process emails...\n")
        
        def process_thread():
            try:
                gmail_apply_rules.set_pause(False)  # Ensure we start unpaused
                
                # Get rules from the rules panel
                rules = []
                for rule_data in self.rules_panel.get_rules():
                    rules.append(GmailRule(
                        name=rule_data['name'],
                        condition=rule_data['condition'],
                        action=rule_data['action']
                    ))
                
                # Apply the rules with UI logging
                gmail_apply_rules.apply_rules(self.service, rules, log_func=self.log)
                wx.CallAfter(self.on_processing_complete)
            except Exception as e:
                wx.CallAfter(self.on_processing_error, str(e))
        
        threading.Thread(target=process_thread).start()
        
    def on_pause(self, event):
        if self.pause_button.GetLabel() == "⏸\nPause":
            gmail_apply_rules.set_pause(True)
            self.pause_button.SetLabel("▶\nResume")
            self.status_text.AppendText("Processing paused...\n")
        else:
            gmail_apply_rules.set_pause(False)
            self.pause_button.SetLabel("⏸\nPause")
            self.status_text.AppendText("Processing resumed...\n")
            
    def on_stop(self, event):
        gmail_apply_rules.set_stop()
        self.status_text.AppendText("Stopping processing...\n")
        self.power_button.Enable()
        self.pause_button.Disable()
        self.stop_button.Disable()
        self.pause_button.SetLabel("⏸\nPause")
        
    def on_processing_complete(self):
        self.status_text.AppendText("Processing completed!\n")
        self.power_button.Enable()
        self.pause_button.Disable()
        self.stop_button.Disable()
        self.pause_button.SetLabel("⏸\nPause")
        
    def on_processing_error(self, error):
        self.status_text.AppendText(f"Error: {error}\n")
        self.power_button.Enable()
        self.pause_button.Disable()
        self.stop_button.Disable()
        self.pause_button.SetLabel("⏸\nPause")
        
    def log(self, message):
        wx.CallAfter(self.status_text.AppendText, f"{message}\n")

class RulesPanel(wx.Panel):
    def __init__(self, parent, service):
        super().__init__(parent)
        self.service = service  # Get the Gmail service directly from the parameter
        self.rules = self.load_rules()
        self.init_ui()
        
    def init_ui(self):
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        # Rules list
        rules_box = wx.StaticBox(self, label="Current Rules")
        rules_sizer = wx.StaticBoxSizer(rules_box, wx.VERTICAL)
        
        # Add delete button above the list
        delete_button = wx.Button(self, label="Delete Selected Rule")
        delete_button.Bind(wx.EVT_BUTTON, self.on_delete_rule)
        rules_sizer.Add(delete_button, 0, wx.ALIGN_RIGHT | wx.ALL, 5)
        
        self.rules_list = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.rules_list.InsertColumn(0, "Condition", width=300)
        self.rules_list.InsertColumn(1, "Action", width=300)
        rules_sizer.Add(self.rules_list, 1, wx.EXPAND | wx.ALL, 5)
        
        # Add rule section
        add_rule_box = wx.StaticBox(self, label="Add New Rule")
        add_rule_sizer = wx.StaticBoxSizer(add_rule_box, wx.VERTICAL)
        
        # Condition
        condition_sizer = wx.BoxSizer(wx.HORIZONTAL)
        condition_sizer.Add(wx.StaticText(self, label="If"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        
        self.condition_field = wx.Choice(self, choices=["Subject", "From", "To"])
        condition_sizer.Add(self.condition_field, 0, wx.RIGHT, 5)
        
        self.condition_operator = wx.Choice(self, choices=["contains", "equals", "starts with", "ends with"])
        condition_sizer.Add(self.condition_operator, 0, wx.RIGHT, 5)
        
        self.condition_value = wx.TextCtrl(self)
        condition_sizer.Add(self.condition_value, 1)
        
        add_rule_sizer.Add(condition_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        # Action
        action_sizer = wx.BoxSizer(wx.HORIZONTAL)
        action_sizer.Add(wx.StaticText(self, label="Then"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        
        self.action_type = wx.Choice(self, choices=["Label as", "Move to"])
        action_sizer.Add(self.action_type, 0, wx.RIGHT, 5)
        
        # Replace text input with label choice
        self.action_value = wx.Choice(self, choices=[])
        self.update_label_choices()  # Populate the label choices
        action_sizer.Add(self.action_value, 1)
        
        add_rule_sizer.Add(action_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        # Add rule button
        add_button = wx.Button(self, label="Add Rule")
        add_button.Bind(wx.EVT_BUTTON, self.on_add_rule)
        add_rule_sizer.Add(add_button, 0, wx.ALIGN_RIGHT | wx.ALL, 5)
        
        # Add refresh button for labels
        refresh_button = wx.Button(self, label="Refresh Labels")
        refresh_button.Bind(wx.EVT_BUTTON, self.on_refresh_labels)
        add_rule_sizer.Add(refresh_button, 0, wx.ALIGN_RIGHT | wx.ALL, 5)
        
        # Layout
        vbox.Add(rules_sizer, 1, wx.EXPAND | wx.ALL, 10)
        vbox.Add(add_rule_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        self.SetSizer(vbox)
        self.update_rules_list()
        
    def update_label_choices(self):
        try:
            # Fetch labels from Gmail API
            labels = self.service.users().labels().list(userId='me').execute().get('labels', [])
            # Get all labels, including system labels
            all_labels = [label['name'] for label in labels]
            # Sort labels alphabetically
            all_labels.sort()
            # Update the choice control
            self.action_value.SetItems(all_labels)
            if all_labels:
                self.action_value.SetSelection(0)
        except Exception as e:
            wx.MessageBox(f"Error fetching labels: {str(e)}", "Error", wx.OK | wx.ICON_ERROR)
        
    def on_refresh_labels(self, event):
        self.update_label_choices()
        
    def load_rules(self):
        try:
            if os.path.exists('rules.json'):
                with open('rules.json', 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return []
        
    def save_rules(self):
        with open('rules.json', 'w') as f:
            json.dump(self.rules, f)
            
    def update_rules_list(self):
        self.rules_list.DeleteAllItems()
        for rule in self.rules:
            condition = f"{rule['condition_field']} {rule['condition_operator']} '{rule['condition_value']}'"
            action = f"{rule['action_type']} '{rule['action_value']}'"
            self.rules_list.Append([condition, action])
            
    def on_add_rule(self, event):
        rule = {
            'condition_field': self.condition_field.GetStringSelection(),
            'condition_operator': self.condition_operator.GetStringSelection(),
            'condition_value': self.condition_value.GetValue(),
            'action_type': self.action_type.GetStringSelection(),
            'action_value': self.action_value.GetStringSelection()
        }
        
        if not all([rule['condition_field'], rule['condition_operator'], 
                   rule['condition_value'], rule['action_type'], rule['action_value']]):
            wx.MessageBox("Please fill in all fields", "Error", wx.OK | wx.ICON_ERROR)
            return
            
        self.rules.append(rule)
        self.save_rules()
        self.update_rules_list()
        
        # Clear fields
        self.condition_value.SetValue("")
        self.action_value.SetSelection(0)  # Reset to first label
        
    def on_delete_rule(self, event):
        selected_index = self.rules_list.GetFirstSelected()
        if selected_index == -1:
            wx.MessageBox("Please select a rule to delete", "No Rule Selected", 
                         wx.OK | wx.ICON_INFORMATION)
            return
            
        # Get the rule details for confirmation
        rule = self.rules[selected_index]
        condition = f"{rule['condition_field']} {rule['condition_operator']} '{rule['condition_value']}'"
        action = f"{rule['action_type']} '{rule['action_value']}'"
        
        # Show confirmation dialog
        msg = f"Are you sure you want to delete this rule?\n\nIf {condition}\nThen {action}"
        dlg = wx.MessageDialog(self, msg, "Confirm Deletion",
                             wx.YES_NO | wx.ICON_QUESTION)
        
        if dlg.ShowModal() == wx.ID_YES:
            # Remove the rule
            self.rules.pop(selected_index)
            self.save_rules()
            self.update_rules_list()
            
        dlg.Destroy()

    def get_rules(self):
        """Return the current rules with their conditions and actions formatted for evaluation."""
        formatted_rules = []
        for rule in self.rules:
            # Create condition function based on the rule type
            def create_condition(rule):
                def condition(msg):
                    headers = msg.get('payload', {}).get('headers', [])
                    header_value = next((h['value'] for h in headers if h['name'] == rule['condition_field']), '')
                    
                    if rule['condition_operator'] == 'contains':
                        return rule['condition_value'].lower() in header_value.lower()
                    elif rule['condition_operator'] == 'equals':
                        return rule['condition_value'].lower() == header_value.lower()
                    elif rule['condition_operator'] == 'starts with':
                        return header_value.lower().startswith(rule['condition_value'].lower())
                    elif rule['condition_operator'] == 'ends with':
                        return header_value.lower().endswith(rule['condition_value'].lower())
                    return False
                return condition

            # Create action function
            def create_action(rule):
                def action(msg, service):
                    label_id = gmail_apply_rules.get_or_create_label(service, rule['action_value'])
                    service.users().messages().modify(
                        userId='me',
                        id=msg['id'],
                        body={'addLabelIds': [label_id]}
                    ).execute()
                return action

            formatted_rules.append({
                'name': f"{rule['condition_field']} {rule['condition_operator']} '{rule['condition_value']}' -> {rule['action_type']} '{rule['action_value']}'",
                'condition': create_condition(rule),
                'action': create_action(rule)
            })
        
        return formatted_rules

class CreateLabelDialog(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="Create New Label", size=(400, 200))
        self.label_name = ""
        self.init_ui()
        
    def init_ui(self):
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        # Label name input
        name_sizer = wx.BoxSizer(wx.HORIZONTAL)
        name_label = wx.StaticText(panel, label="Label Name:")
        self.name_input = wx.TextCtrl(panel)
        name_sizer.Add(name_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        name_sizer.Add(self.name_input, 1, wx.EXPAND)
        
        vbox.Add(name_sizer, 0, wx.EXPAND | wx.ALL, 20)
        
        # Buttons
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        ok_button = wx.Button(panel, wx.ID_OK, "Create")
        cancel_button = wx.Button(panel, wx.ID_CANCEL, "Cancel")
        button_sizer.Add(ok_button, 0, wx.RIGHT, 5)
        button_sizer.Add(cancel_button, 0)
        
        vbox.Add(button_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 20)
        
        panel.SetSizer(vbox)
        self.Centre()
        
        # Bind events
        ok_button.Bind(wx.EVT_BUTTON, self.on_ok)
        
    def on_ok(self, event):
        self.label_name = self.name_input.GetValue().strip()
        if not self.label_name:
            wx.MessageBox("Please enter a label name", "Error", wx.OK | wx.ICON_ERROR)
            return
        self.EndModal(wx.ID_OK)

class LabelsPanel(wx.Panel):
    def __init__(self, parent, service):
        super().__init__(parent)
        self.service = service  # Get the Gmail service directly from the parameter
        self.init_ui()
        
    def init_ui(self):
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        # Labels list
        labels_box = wx.StaticBox(self, label="Gmail Labels")
        labels_sizer = wx.StaticBoxSizer(labels_box, wx.VERTICAL)
        
        # Add create button above the list
        create_button = wx.Button(self, label="Create New Label")
        create_button.Bind(wx.EVT_BUTTON, self.on_create_label)
        labels_sizer.Add(create_button, 0, wx.ALIGN_RIGHT | wx.ALL, 5)
        
        self.labels_list = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.labels_list.InsertColumn(0, "Label Name", width=300)
        self.labels_list.InsertColumn(1, "Type", width=200)
        labels_sizer.Add(self.labels_list, 1, wx.EXPAND | wx.ALL, 5)
        
        # Add delete button below the list
        delete_button = wx.Button(self, label="Delete Selected Label")
        delete_button.Bind(wx.EVT_BUTTON, self.on_delete_label)
        labels_sizer.Add(delete_button, 0, wx.ALIGN_RIGHT | wx.ALL, 5)
        
        vbox.Add(labels_sizer, 1, wx.EXPAND | wx.ALL, 10)
        
        self.SetSizer(vbox)
        self.update_labels_list()
        
    def update_labels_list(self):
        self.labels_list.DeleteAllItems()
        try:
            # Fetch labels from Gmail API
            labels = self.service.users().labels().list(userId='me').execute().get('labels', [])
            for label in labels:
                label_name = label['name']
                label_type = label.get('type', 'User')
                self.labels_list.Append([label_name, label_type])
        except Exception as e:
            wx.MessageBox(f"Error fetching labels: {str(e)}", "Error", wx.OK | wx.ICON_ERROR)
        
    def on_create_label(self, event):
        dlg = CreateLabelDialog(self)
        if dlg.ShowModal() == wx.ID_OK:
            label_name = dlg.label_name
            try:
                # Create label using Gmail API
                label_body = {
                    'name': label_name,
                    'labelListVisibility': 'labelShow',
                    'messageListVisibility': 'show'
                }
                self.service.users().labels().create(userId='me', body=label_body).execute()
                self.update_labels_list()
                wx.MessageBox(f"Label '{label_name}' created successfully!", "Success", wx.OK | wx.ICON_INFORMATION)
            except Exception as e:
                wx.MessageBox(f"Error creating label: {str(e)}", "Error", wx.OK | wx.ICON_ERROR)
        dlg.Destroy()
        
    def on_delete_label(self, event):
        selected_index = self.labels_list.GetFirstSelected()
        if selected_index == -1:
            wx.MessageBox("Please select a label to delete", "No Label Selected", 
                         wx.OK | wx.ICON_INFORMATION)
            return
            
        label_name = self.labels_list.GetItem(selected_index, 0).GetText()
        label_type = self.labels_list.GetItem(selected_index, 1).GetText()
        
        # Don't allow deletion of system labels
        if label_type == 'System':
            wx.MessageBox("Cannot delete system labels", "Error", wx.OK | wx.ICON_ERROR)
            return
        
        # Show confirmation dialog
        msg = f"Are you sure you want to delete the label '{label_name}'?"
        dlg = wx.MessageDialog(self, msg, "Confirm Deletion",
                             wx.YES_NO | wx.ICON_QUESTION)
        
        if dlg.ShowModal() == wx.ID_YES:
            try:
                # Get the label ID
                labels = self.service.users().labels().list(userId='me').execute().get('labels', [])
                label_id = next((label['id'] for label in labels if label['name'] == label_name), None)
                
                if label_id:
                    # Delete label using Gmail API
                    self.service.users().labels().delete(userId='me', id=label_id).execute()
                    self.update_labels_list()
                    wx.MessageBox(f"Label '{label_name}' deleted successfully!", "Success", wx.OK | wx.ICON_INFORMATION)
                else:
                    wx.MessageBox(f"Label '{label_name}' not found", "Error", wx.OK | wx.ICON_ERROR)
            except Exception as e:
                wx.MessageBox(f"Error deleting label: {str(e)}", "Error", wx.OK | wx.ICON_ERROR)
            
        dlg.Destroy()

class SettingsPanel(wx.Panel):
    def __init__(self, parent, service, app):
        super().__init__(parent)
        self.service = service
        self.app = app
        self.init_ui()
        
    def init_ui(self):
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        # Add some space at the top
        vbox.AddSpacer(20)
        
        # Account info box
        account_box = wx.StaticBox(self, label="Account Information")
        account_sizer = wx.StaticBoxSizer(account_box, wx.VERTICAL)
        
        # Create a grid for account info
        grid = wx.FlexGridSizer(3, 2, 10, 20)  # 3 rows, 2 columns, 10px vertical gap, 20px horizontal gap
        
        # Create labels and values
        self.email_label = wx.StaticText(self, label="📧 Email Address:")
        self.email_value = wx.StaticText(self, label="")
        self.messages_label = wx.StaticText(self, label="📨 Total Messages:")
        self.messages_value = wx.StaticText(self, label="")
        self.threads_label = wx.StaticText(self, label="📝 Total Threads:")
        self.threads_value = wx.StaticText(self, label="")
        
        # Set font for labels
        label_font = wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        self.email_label.SetFont(label_font)
        self.messages_label.SetFont(label_font)
        self.threads_label.SetFont(label_font)
        
        # Set font for values
        value_font = wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.email_value.SetFont(value_font)
        self.messages_value.SetFont(value_font)
        self.threads_value.SetFont(value_font)
        
        # Add to grid
        grid.Add(self.email_label, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.email_value, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.messages_label, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.messages_value, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.threads_label, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.threads_value, 0, wx.ALIGN_CENTER_VERTICAL)
        
        account_sizer.Add(grid, 0, wx.ALL, 20)
        vbox.Add(account_sizer, 0, wx.EXPAND | wx.ALL, 20)
        
        # Add a separator line
        line = wx.StaticLine(self)
        vbox.Add(line, 0, wx.EXPAND | wx.ALL, 20)
        
        # Account actions box
        actions_box = wx.StaticBox(self, label="Account Actions")
        actions_sizer = wx.StaticBoxSizer(actions_box, wx.VERTICAL)
        
        # Add some description text
        description = wx.StaticText(self, label="You can log out of your Gmail account here. This will remove your authentication token and require you to log in again.")
        description.Wrap(400)  # Wrap text to fit width
        actions_sizer.Add(description, 0, wx.ALL, 20)
        
        # Logout button with better styling
        logout_button = wx.Button(self, label="Logout")
        logout_button.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        logout_button.Bind(wx.EVT_BUTTON, self.on_logout)
        actions_sizer.Add(logout_button, 0, wx.ALIGN_CENTER | wx.ALL, 20)
        
        vbox.Add(actions_sizer, 0, wx.EXPAND | wx.ALL, 20)
        
        # Add some space at the bottom
        vbox.AddSpacer(20)
        
        self.SetSizer(vbox)
        self.update_account_info()
        
    def update_account_info(self):
        if not self.service:
            self.email_value.SetLabel("Not connected to Gmail")
            self.messages_value.SetLabel("")
            self.threads_value.SetLabel("")
            return
            
        try:
            profile = self.service.users().getProfile(userId='me').execute()
            email = profile.get('emailAddress', 'Unknown')
            total_messages = profile.get('messagesTotal', 'Unknown')
            threads_total = profile.get('threadsTotal', 'Unknown')
            
            self.email_value.SetLabel(email)
            self.messages_value.SetLabel(f"{total_messages:,}")
            self.threads_value.SetLabel(f"{threads_total:,}")
        except Exception as e:
            self.email_value.SetLabel(f"Error: {str(e)}")
            self.messages_value.SetLabel("")
            self.threads_value.SetLabel("")
            
    def on_logout(self, event):
        if os.path.exists('token.json'):
            try:
                os.remove('token.json')
            except Exception as e:
                wx.MessageBox(f"Error removing token file: {str(e)}", "Error", wx.OK | wx.ICON_ERROR)
                return
        
        # Show the auth frame through the app
        self.app.show_auth_frame()

def authenticate_gmail():
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

def main():
    app = MainApp()
    app.MainLoop()

if __name__ == '__main__':
    main() 