import os
import re
import csv
import ftplib
import requests
import logging
from tkinter import Tk, Button, Label, messagebox, Listbox, Scrollbar, END, Entry, StringVar, Frame, Toplevel
from datetime import datetime
from tkinter import ttk

# === CONFIGURATION ===
VALID_DIR = "valid_files"
ERROR_LOG_DIR = "error_logs"
ERROR_LOG_FILE = os.path.join(ERROR_LOG_DIR, "error_log.txt")
EXPECTED_HEADERS = ["batch_id", "timestamp"] + \
    [f"reading{i}" for i in range(1, 11)]


class FileValidator:
    @staticmethod
    def validate(file_content):
        try:
            reader = csv.reader(file_content.splitlines())
            headers = next(reader, None)
            if headers != EXPECTED_HEADERS:
                return False, f"Incorrect or missing headers: {headers}"
            batch_ids = set()
            for row_num, row in enumerate(reader, start=2):
                if len(row) != 12:
                    return False, f"Row {row_num} has missing columns"
                batch_id = row[0]
                if batch_id in batch_ids:
                    return False, f"Duplicate batch_id {batch_id} on row {row_num}"
                batch_ids.add(batch_id)
                for i, reading in enumerate(row[2:], start=1):
                    try:
                        value = float(reading)
                        if value > 9.9:
                            return False, f"Value exceeds 9.9 in reading{i} on row {row_num}: {value}"
                        if not re.match(r"^\d+(\.\d{1,3})?$", reading):
                            return False, f"Invalid decimal format in reading{i} on row {row_num}: {reading}"
                    except ValueError:
                        return False, f"Non-numeric reading{i} on row {row_num}: {reading}"
        except Exception as e:
            return False, f"Malformed file error: {str(e)}"
        return True, "Valid"


class Logger:
    def __init__(self):
        self.ensure_directories()
        # Clear the error log file at startup
        if os.path.exists(ERROR_LOG_FILE):
            # Truncate the file to clear old logs
            open(ERROR_LOG_FILE, 'w').close()
        logging.basicConfig(
            filename=ERROR_LOG_FILE,
            filemode='a',  # Append mode ensures new logs are added
            level=logging.ERROR,
            format="%(asctime)s - ERROR - [UUID: %(uuid)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    def ensure_directories(self):
        os.makedirs(VALID_DIR, exist_ok=True)
        os.makedirs(ERROR_LOG_DIR, exist_ok=True)

    def get_uuid(self):
        try:
            response = requests.get(
                "https://www.uuidtools.com/api/generate/v1")
            response.raise_for_status()
            uuid_list = response.json()
            return uuid_list[0] if uuid_list else "unknown_uuid"
        except Exception as e:
            logging.error(f"UUID generation failed: {str(e)}", extra={
                          "uuid": "unknown_uuid"})
            return "unknown_uuid"

    def log(self, message):
        uuid = self.get_uuid()
        logging.error(message, extra={"uuid": uuid})


class FTPClient:
    def __init__(self):
        self.ftp = None
        self.downloaded_files = []

    def connect(self, host, user, password):
        self.ftp = ftplib.FTP()
        self.ftp.connect(host)
        self.ftp.login(user, password)

    def list_files(self):
        return self.ftp.nlst()

    def search_files(self, keyword):
        all_files = self.list_files()
        matched_files = [f for f in all_files if keyword in f]

        if not matched_files:
            messagebox.showerror('Error', "There is no file with this name!")

        return matched_files

    def download_file(self, filename):
        # content = []
        # self.ftp.retrbinary(f'RETR {filename}', content.append)
        # return "\n".join(content)
        from io import StringIO
        content = []

        def handle_binary(data):
            content.append(data.decode("utf-8"))

        self.ftp.retrbinary(f'RETR {filename}', callback=handle_binary)
        return ''.join(content)

    def is_connected(self):
        return self.ftp is not None


class DownloadStatus:
    def __init__(self):
        self.status = 'Idle'
        self.status_label = None

    def set_status_label(self, label):
        self.status_label = label

    def change_status(self, type):
        if (type == "start"):
            self.status = 'Downloading...'
        elif (type == "success"):
            self.status = 'Download Success'
        else:
            self.status = 'Download Failed!'

        # Update the status label if it exists
        if self.status_label:
            self.status_label.config(text=self.status)

        return self.status


class App:
    def __init__(self, root):
        self.root = root
        self.search_var = StringVar()
        self.ftp_client = FTPClient()
        self.logger = Logger()
        self.file_listbox = None
        self.valid_files_listbox = None
        self.error_logs_listbox = None
        self.download_status = DownloadStatus()
        self.build_gui()

    def build_gui(self):
        self.root.title("FTP CSV Validator")
        self.root.geometry("800x600")

        main_frame = Frame(self.root)
        main_frame.pack(padx=10, pady=10, fill="both", expand=True)

        # Connection Frame
        connection_frame = Frame(main_frame)
        connection_frame.pack(fill="x", pady=5)
        Label(connection_frame, text="FTP Connection",
              font=("Arial", 12, "bold")).pack(anchor="w")
        Button(connection_frame, text="Connect to FTP",
               command=self.connect_ftp_form, width=20).pack(side="left", padx=5)

        # Available Files Frame
        header_frame = Frame(main_frame)
        header_frame.pack(fill="both", expand=True)
        Label(header_frame, text="Available Files", font=(
            "Arial", 12, "bold")).pack(side="left")
        Label(header_frame, text="Download status: ",
              font=("Arial", 12, "bold")).pack(side="left")

        # Create status label and set it in download_status
        status_label = Label(header_frame, text=self.download_status.status,
                             font=("Arial", 12, "bold"))
        status_label.pack(side="left")
        self.download_status.set_status_label(status_label)

        # Search Frame
        search_frame = Frame(header_frame)
        search_frame.pack(side="right")
        self.search_entry = Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side="left")
        Button(search_frame, text="Search",
               command=self.searchFileName).pack(side="left", padx=3)
        Button(search_frame, text="Clear Search",
               command=self.clearSearch).pack(side="right")

        # Bind the <Return> key to the search function
        self.search_entry.bind("<Return>", lambda event: self.searchFileName())

        # Available Files Frame
        file_frame = Frame(main_frame)
        file_frame.pack(fill="both", expand=True, pady=5)
        self.file_listbox = Listbox(file_frame, width=60, height=10)
        self.file_listbox.pack(side="left", fill="both", expand=True)

        scrollbar = Scrollbar(file_frame)
        scrollbar.pack(side="right", fill="y")
        self.file_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.file_listbox.yview)

        # Buttons Frame
        button_frame = Frame(main_frame)
        button_frame.pack(fill="x", pady=5)
        Button(button_frame, text="List Files", command=self.list_files,
               width=20).pack(side="left", padx=5)
        Button(button_frame, text="Download Selected File",
               command=self.download_selected_file, width=25).pack(side="left", padx=5)

        # Valid Files Frame
        valid_files_frame = Frame(main_frame)
        valid_files_frame.pack(fill="both", expand=True, pady=5)
        Label(valid_files_frame, text="Valid Files", font=(
            "Arial", 12, "bold")).pack(anchor="w", pady=5)
        self.valid_files_listbox = Listbox(
            valid_files_frame, width=60, height=5)
        self.valid_files_listbox.pack(side="left", fill="both", expand=True)

        valid_scrollbar = Scrollbar(valid_files_frame)
        valid_scrollbar.pack(side="right", fill="y")
        self.valid_files_listbox.config(yscrollcommand=valid_scrollbar.set)
        valid_scrollbar.config(command=self.valid_files_listbox.yview)

        # Error Logs Frame
        error_logs_frame = Frame(main_frame)
        error_logs_frame.pack(fill="both", expand=True, pady=5)
        Label(error_logs_frame, text="Error Logs", font=(
            "Arial", 12, "bold")).pack(anchor="w", pady=5)
        self.error_logs_listbox = Listbox(error_logs_frame, width=60, height=5)
        self.error_logs_listbox.pack(side="left", fill="both", expand=True)

        error_scrollbar = Scrollbar(error_logs_frame)
        error_scrollbar.pack(side="right", fill="y")
        self.error_logs_listbox.config(yscrollcommand=error_scrollbar.set)
        error_scrollbar.config(command=self.error_logs_listbox.yview)

        # Removed the call to load_error_logs() here
        # This ensures error logs are not loaded on startup

    def connect_ftp_form(self):
        def connect():
            try:
                self.ftp_client.connect(
                    host_var.get(), user_var.get(), pass_var.get())
                messagebox.showinfo("Success", "Connected to FTP Server")
                ftp_window.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"FTP connection failed: {e}")

        ftp_window = Toplevel(self.root)
        ftp_window.title("FTP Connection")

        Label(ftp_window, text="Hostname:").grid(
            row=0, column=0, padx=5, pady=5)
        host_var = StringVar()
        Entry(ftp_window, textvariable=host_var).grid(
            row=0, column=1, padx=5, pady=5)

        Label(ftp_window, text="Username:").grid(
            row=1, column=0, padx=5, pady=5)
        user_var = StringVar()
        Entry(ftp_window, textvariable=user_var).grid(
            row=1, column=1, padx=5, pady=5)

        Label(ftp_window, text="Password:").grid(
            row=2, column=0, padx=5, pady=5)
        pass_var = StringVar()
        Entry(ftp_window, textvariable=pass_var,
              show="*").grid(row=2, column=1, padx=5, pady=5)

        Button(ftp_window, text="Connect", command=connect).grid(
            row=3, column=0, columnspan=2, pady=10)

    def list_files(self):
        if not self.ftp_client.is_connected():
            messagebox.showerror("Error", "Not connected to FTP")
            return
        try:
            files = self.ftp_client.list_files()
            self.file_listbox.delete(0, END)
            for file in files:
                self.file_listbox.insert(END, file)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to list files: {e}")

    def searchFileName(self):
        if not self.ftp_client.is_connected():
            messagebox.showerror("Error", "Not connected to FTP")
            return
        search_value = self.search_var.get().strip()
        if not search_value:
            messagebox.showerror("Error", "Please enter search keyword")
            return
        try:
            found_files = self.ftp_client.search_files(search_value)
            self.file_listbox.delete(0, END)
            for file in found_files:
                self.file_listbox.insert(END, file)
        except Exception as e:
            messagebox.showerror("Error", f"Search failed: {e}")

    def clearSearch(self):
        self.search_var.set('')

    def download_selected_file(self):
        self.download_status.change_status("start")
        if not self.ftp_client.is_connected():
            self.download_status.change_status("error")
            messagebox.showerror("Error", "Not connected to FTP")
            return

        selected = self.file_listbox.curselection()
        if not selected:
            self.download_status.change_status("error")
            messagebox.showerror("Error", "No file selected")
            return

        filename = self.file_listbox.get(selected)

        # If file is already downloaded or attempted, skip re-downloading
        if filename in self.ftp_client.downloaded_files:
            self.download_status.change_status("error")
            messagebox.showwarning(
                "Warning", f"File '{filename}' already downloaded or attempted.")
            return

        # New Validation: Check file extension
        if not filename.lower().endswith('.csv'):
            error_msg = f"Invalid file extension for '{filename}'. Only '.csv' files are allowed."
            self.download_status.change_status("error")
            self.logger.log(error_msg)
            self.load_error_logs()
            messagebox.showerror("Invalid File", error_msg)
            self.ftp_client.downloaded_files.append(filename)
            return

        try:
            size = self.ftp_client.ftp.size(filename)
            if size == 0:
                error_msg = f"File '{filename}' is empty (zero size)."
                self.download_status.change_status("error")
                self.logger.log(error_msg)
                self.load_error_logs()
                messagebox.showwarning("Warning", error_msg)
                self.ftp_client.downloaded_files.append(filename)
                return
        except Exception as e:
            self.download_status.change_status("error")
            self.logger.log(f"Download size check error: {str(e)}")
            self.load_error_logs()
            self.ftp_client.downloaded_files.append(filename)
            return

        try:
            content = self.ftp_client.download_file(filename)
            valid, msg = FileValidator.validate(content)
            if valid:
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                new_filename = f"MED_DATA_{timestamp}.csv"
                path = os.path.join(VALID_DIR, new_filename)
                with open(path, 'w') as f:
                    f.write(content)
                self.valid_files_listbox.insert(END, new_filename)
                self.valid_files_listbox.see(END)
                self.valid_files_listbox.selection_clear(0, END)
                self.valid_files_listbox.selection_set(END)
                self.download_status.change_status("success")
                messagebox.showinfo(
                    "Success", f"File saved as '{new_filename}' in '{VALID_DIR}'.")
            else:
                self.download_status.change_status("error")
                self.logger.log(f"Validation failed for '{filename}': {msg}")
                self.load_error_logs()
                messagebox.showerror("Validation Error",
                                     f"Validation failed:\n{msg}")
        except Exception as e:
            self.download_status.change_status("error")
            self.logger.log(f"Download error: {str(e)}")
            self.load_error_logs()
            messagebox.showerror(
                "Download Error", f"Failed to download/process file:\n{e}")
        finally:
            # Mark file as attempted
            self.ftp_client.downloaded_files.append(filename)

    def load_error_logs(self):
        """Load error logs from the file and update the error_logs_listbox."""
        try:
            if os.path.exists(ERROR_LOG_FILE):
                with open(ERROR_LOG_FILE, "r") as file:
                    logs = file.readlines()
                self.error_logs_listbox.delete(0, END)
                for log in logs:
                    self.error_logs_listbox.insert(END, log.strip())
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load error logs: {e}")


if __name__ == '__main__':
    root = Tk()
    app = App(root)
    root.mainloop()


# def download_selected_file(self):
#         import time

#         download_window = Toplevel(self.root, padx=10, pady=10)
#         download_window.title("Downloading Status")

#         download_label = Label(download_window, text="Downloading...")
#         download_label.pack(padx=10, pady=10)

#         progressbar = ttk.Progressbar(download_window, length=300, mode='determinate')
#         progressbar.pack(padx=10, pady=10)

#         # Start progress bar animation
#         def update_progress():
#             for i in range(11):  # 0 to 10 steps
#                 progressbar['value'] = i * 10  # Each step is 10%
#                 download_window.update()
#                 time.sleep(1)  # Wait for 1 second between each step

#         # Start the progress bar animation in a separate thread
#         import threading
#         progress_thread = threading.Thread(target=update_progress)
#         progress_thread.start()

#         self.download_status.change_status("start")
#         if not self.ftp_client.is_connected():
#             messagebox.showerror("Error", "Not connected to FTP")
#             return
#         selected = self.file_listbox.curselection()
#         if not selected:
#             messagebox.showerror("Error", "No file selected")
#             self.download_status.change_status("error")
#             return

#         filename = self.file_listbox.get(selected)

#         # If file is already downloaded or attempted, skip re-downloading
#         if filename in self.ftp_client.downloaded_files:
#             messagebox.showwarning(
#                 "Warning", f"File '{filename}' already downloaded or attempted.")
#             self.download_status.change_status("error")
#             return

#         # New Validation: Check file extension
#         if not filename.lower().endswith('.csv'):
#             error_msg = f"Invalid file extension for '{filename}'. Only '.csv' files are allowed."
#             self.logger.log(error_msg)
#             self.load_error_logs()
#             messagebox.showerror("Invalid File", error_msg)
#             self.ftp_client.downloaded_files.append(
#                 filename)  # Mark as attempted
#             self.download_status.change_status("error")
#             return

#         try:
#             size = self.ftp_client.ftp.size(filename)
#             if size == 0:
#                 error_msg = f"File '{filename}' is empty (zero size)."
#                 self.logger.log(error_msg)
#                 self.load_error_logs()
#                 messagebox.showwarning("Warning", error_msg)
#                 self.ftp_client.downloaded_files.append(
#                     filename)  # Mark as attempted
#                 self.download_status.change_status("error")
#                 return
#         except Exception as e:
#             self.logger.log(f"Download size check error: {str(e)}")
#             self.load_error_logs()
#             self.ftp_client.downloaded_files.append(
#                 filename)  # Mark as attempted
#             self.download_status.change_status("error")
#             return  # Don't proceed if error

#         try:
#             content = self.ftp_client.download_file(filename)
#             valid, msg = FileValidator.validate(content)
#             if valid:
#                 timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
#                 new_filename = f"MED_DATA_{timestamp}.csv"
#                 path = os.path.join(VALID_DIR, new_filename)
#                 with open(path, 'w') as f:
#                     f.write(content)
#                 self.valid_files_listbox.insert(END, new_filename)
#                 self.valid_files_listbox.see(END)  # Auto-scroll to the bottom
#                 self.valid_files_listbox.selection_clear(0, END)
#                 self.valid_files_listbox.selection_set(
#                     END)  # Highlight newly added file
#                 messagebox.showinfo(
#                     "Success", f"File saved as '{new_filename}' in '{VALID_DIR}'.")
#                 self.download_status.change_status("success")
#             else:
#                 self.logger.log(f"Validation failed for '{filename}': {msg}")
#                 self.load_error_logs()
#                 messagebox.showerror("Validation Error",
#                                      f"Validation failed:\n{msg}")
#                 self.download_status.change_status("error")
#         except Exception as e:
#             self.logger.log(f"Download error: {str(e)}")
#             self.load_error_logs()
#             messagebox.showerror(
#                 "Download Error", f"Failed to download/process file:\n{e}")
#             self.download_status.change_status("error")
#         finally:
#             # Mark file as attempted no matter what (success or failure)
#             self.ftp_client.downloaded_files.append(filename)
#             # Wait for progress bar to complete if it hasn't already
#             progress_thread.join()
#             # Close the download window
#             download_window.destroy()
