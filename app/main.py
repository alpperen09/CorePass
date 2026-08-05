"""
main.py
-------
CorePass masaüstü uygulamasının giriş noktası.
Çalıştırmak için: python main.py
(veya PyInstaller ile CorePass.exe olarak derlenmiş hali)
"""

from gui import CorePassApp

if __name__ == "__main__":
    app = CorePassApp()
    app.mainloop()
