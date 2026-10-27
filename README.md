VaultLite 🔐
A free, community-made offline password manager for Windows and desktop use.

VaultLite is a personal project created by Jagdish Sejpal and shared with the community for free. It is built with Python and provides a simple way to organize website credentials locally, with encrypted password storage and a password generator.
Please note: VaultLite is a community project and has not been independently security-audited. Do not rely on it to protect critical or highly sensitive accounts without conducting your own review and testing.

✨ Features
- Master-password account registration and login
- Encrypted storage for saved passwords
- Local SQLite database
- Add, search, edit, reveal, and delete saved credentials
- Generate strong passwords with configurable character types
- Session inactivity timeout
- Desktop window mode through PyWebView
- Optional offline license/trial functionality in the current code
🧰 Built With
- Python
- Flask
- SQLite
- Cryptography (Fernet and Scrypt)
- Waitress
- PyWebView
🚀 Run from Source
Requirements
- Python 3.12 recommended
- Git
Setup
1. Clone this repository:
   git clone https://github.com/YOUR-USERNAME/VaultLite.git
   cd VaultLite
2. Create a virtual environment:
   python -m venv .venv
3. Activate it on Windows:
   .venv\Scripts\activate
4. Install the dependencies:
   pip install -r requirements.txt
5. Start the app in your browser:
   python app.py
6. Open http://127.0.0.1:5000 in your browser.
To try desktop-window mode, run:
python launcher.py
The repository must include the required templates/ and static/ folders for the app to run. Desktop mode may require the Windows WebView2 runtime.
📦 Windows Installer
A prebuilt .exe installer is not included unless one is explicitly published in the repository's Releases section. The project contains build-related files intended to create a Windows installer; the build process should be tested before distributing it.
🔐 Privacy & Security Notes
- VaultLite is designed to store its database locally on your computer.
- The app encrypts saved passwords and derives an encryption key from the master password.
- Keep your master password safe. There is no master-password recovery process.
- Back up your local VaultLite data before reinstalling or making major changes.
- Review the source code and test it before using it with real credentials.
- Do not upload your personal vault database, license files, private signing keys, or customer records to GitHub.
🤝 Free for the Community
This project is shared for community learning and use at no cost. Contributions, bug reports, suggestions, and constructive feedback are welcome.

To contribute:
1. Open an issue describing a bug or improvement.
2. Share clear steps to reproduce bugs.
3. Submit a pull request for changes, if you are comfortable with Git.
📄 License
No open-source license has been specified yet. Until a LICENSE file is added, don't assume that others have permission to redistribute or modify the code. If you want this project to be free for the community with clear reuse rights, choose and add an appropriate license (for example, MIT) before publishing.
👨‍💻 Author
Jagdish Sejpal

Made as a community project. Shared free of charge.
