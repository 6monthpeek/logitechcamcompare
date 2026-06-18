import sys
import os
from PySide6.QtWidgets import QApplication
from src.ui.main_window import MainWindow

def main():
    # Application Entry Point
    app = QApplication(sys.argv)
    
    # Load and apply QSS stylesheet globally
    qss_path = os.path.join(os.path.dirname(__file__), "src", "ui", "styles.qss")
    try:
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except Exception as e:
        print(f"Failed to load QSS stylesheet: {e}")
    
    # Instantiate and display the MainWindow
    window = MainWindow()
    window.show()
    
    # Execute the application event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
