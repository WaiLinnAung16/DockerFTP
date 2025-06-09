import unittest
from datetime import datetime
from Testfile10 import FileValidator, Logger, FTPClient, DownloadStatus, App, VALID_DIR, ERROR_LOG_DIR, ERROR_LOG_FILE, EXPECTED_HEADERS

class TestFileValidator(unittest.TestCase):
    def setUp(self):
        self.validator = FileValidator()
        self.valid_csv_content = """batch_id,timestamp,reading1,reading2,reading3,reading4,reading5,reading6,reading7,reading8,reading9,reading10
1,2023-01-01,1.234,2.345,3.456,4.567,5.678,6.789,7.890,8.901,9.012,0.123
2,2023-01-02,1.234,2.345,3.456,4.567,5.678,6.789,7.890,8.901,9.012,0.123"""

    def test_valid_file(self):
        is_valid, message = FileValidator.validate(self.valid_csv_content)
        self.assertTrue(is_valid)
        self.assertEqual(message, "Valid")

    def test_invalid_headers(self):
        invalid_headers = """wrong_id,timestamp,reading1,reading2,reading3,reading4,reading5,reading6,reading7,reading8,reading9,reading10
1,2023-01-01,1.234,2.345,3.456,4.567,5.678,6.789,7.890,8.901,9.012,0.123"""
        is_valid, message = FileValidator.validate(invalid_headers)
        self.assertFalse(is_valid)
        self.assertIn("Incorrect or missing headers", message)

    def test_duplicate_batch_id(self):
        duplicate_batch = """batch_id,timestamp,reading1,reading2,reading3,reading4,reading5,reading6,reading7,reading8,reading9,reading10
1,2023-01-01,1.234,2.345,3.456,4.567,5.678,6.789,7.890,8.901,9.012,0.123
1,2023-01-02,1.234,2.345,3.456,4.567,5.678,6.789,7.890,8.901,9.012,0.123"""
        is_valid, message = FileValidator.validate(duplicate_batch)
        self.assertFalse(is_valid)
        self.assertIn("Duplicate batch_id", message)

    def test_invalid_decimal_format(self):
        invalid_decimal = """batch_id,timestamp,reading1,reading2,reading3,reading4,reading5,reading6,reading7,reading8,reading9,reading10
1,2023-01-01,1.234,2.345,3.456,4.567,5.678,6.789,7.890,8.901,9.012,0.1234"""
        is_valid, message = FileValidator.validate(invalid_decimal)
        self.assertFalse(is_valid)
        self.assertIn("Invalid decimal format", message)

    def test_value_exceeds_limit(self):
        exceeds_limit = """batch_id,timestamp,reading1,reading2,reading3,reading4,reading5,reading6,reading7,reading8,reading9,reading10
1,2023-01-01,1.234,2.345,3.456,4.567,5.678,6.789,7.890,8.901,9.012,10.123"""
        is_valid, message = FileValidator.validate(exceeds_limit)
        self.assertFalse(is_valid)
        self.assertIn("Value exceeds 9.9", message)


class TestDownloadStatus(unittest.TestCase):
    def setUp(self):
        self.status = DownloadStatus()

    def test_status_changes(self):
        self.assertEqual(self.status.change_status("start"), "Downloading...")
        self.assertEqual(self.status.change_status(
            "success"), "Download Success")
        self.assertEqual(self.status.change_status(
            "error"), "Download Failed!")


if __name__ == '__main__':
    unittest.main()


# class TestAppIntegration(unittest.TestCase):
#     def setUp(self):
#         self.temp_dir = tempfile.mkdtemp()
#         self.original_valid_dir = VALID_DIR
#         self.original_error_log_dir = ERROR_LOG_DIR

#     def tearDown(self):
#         shutil.rmtree(self.temp_dir)

#     @patch('tkinter.Tk')
#     def test_app_initialization(self, mock_tk):
#         mock_root = MagicMock()
#         mock_tk.return_value = mock_root
#         app = App(mock_root)
#         self.assertIsNotNone(app.ftp_client)
#         self.assertIsNotNone(app.logger)
#         self.assertIsNotNone(app.file_listbox)
#         self.assertIsNotNone(app.valid_files_listbox)
#         self.assertIsNotNone(app.error_logs_listbox)

#     @patch('tkinter.Tk')
#     @patch('ftplib.FTP')
#     def test_ftp_connection(self, mock_ftp, mock_tk):
#         mock_root = MagicMock()
#         mock_tk.return_value = mock_root
#         mock_ftp_instance = MagicMock()
#         mock_ftp.return_value = mock_ftp_instance

#         app = App(mock_root)
#         app.ftp_client.connect("host", "user", "pass")

#         mock_ftp_instance.login.assert_called_once_with("user", "pass")
#         self.assertTrue(app.ftp_client.is_connected())
# class TestLogger(unittest.TestCase):
#     def setUp(self):
#         self.logger = Logger()
#         self.temp_dir = tempfile.mkdtemp()
#         self.original_error_log_dir = ERROR_LOG_DIR
#         self.original_error_log_file = ERROR_LOG_FILE

#     def tearDown(self):
#         shutil.rmtree(self.temp_dir)

#     @patch('requests.get')
#     def test_get_uuid_success(self, mock_get):
#         mock_get.return_value.json.return_value = ["test-uuid-123"]
#         uuid = self.logger.get_uuid()
#         self.assertEqual(uuid, "test-uuid-123")

#     @patch('requests.get')
#     def test_get_uuid_failure(self, mock_get):
#         mock_get.side_effect = Exception("Connection error")
#         uuid = self.logger.get_uuid()
#         self.assertEqual(uuid, "unknown_uuid")

#     def test_log_message(self):
#         with patch('logging.error') as mock_logging:
#             self.logger.log("Test error message")
#             mock_logging.assert_called_once()

# class TestFTPClient(unittest.TestCase):
#     def setUp(self):
#         self.ftp_client = FTPClient()

#     @patch('ftplib.FTP')
#     def test_connect_success(self, mock_ftp):
#         mock_ftp_instance = MagicMock()
#         mock_ftp.return_value = mock_ftp_instance
#         self.ftp_client.connect("host", "user", "pass")
#         mock_ftp_instance.login.assert_called_once_with("user", "pass")

#     @patch('ftplib.FTP')
#     def test_connect_failure(self, mock_ftp):
#         mock_ftp.side_effect = Exception("Connection failed")
#         with self.assertRaises(Exception):
#             self.ftp_client.connect("host", "user", "pass")

#     @patch('ftplib.FTP')
#     def test_list_files(self, mock_ftp):
#         mock_ftp_instance = MagicMock()
#         mock_ftp_instance.nlst.return_value = ["file1.csv", "file2.csv"]
#         self.ftp_client.ftp = mock_ftp_instance
#         files = self.ftp_client.list_files()
#         self.assertEqual(files, ["file1.csv", "file2.csv"])

#     @patch('ftplib.FTP')
#     def test_search_files(self, mock_ftp):
#         mock_ftp_instance = MagicMock()
#         mock_ftp_instance.nlst.return_value = ["test1.csv", "test2.csv", "other.txt"]
#         self.ftp_client.ftp = mock_ftp_instance
#         found_files = self.ftp_client.search_files("test")
#         self.assertEqual(found_files, ["test1.csv", "test2.csv"])
