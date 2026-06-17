import sys
from PySide6.QtWidgets import QApplication
from src.ui.main_window import MainWindow

def main():
    # Application Entry Point
    app = QApplication(sys.argv)
    
    # Instantiate and display the MainWindow
    window = MainWindow()
    window.show()
    
    # Execute the application event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
