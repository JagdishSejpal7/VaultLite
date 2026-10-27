# VaultLite - build & sell guide

## 1. Build the product (one double-click)
On a Windows PC: double-click **build.bat**.
It installs Python 3.12 and Inno Setup if missing (via winget), builds the app and creates:

    release\VaultLite-Setup-1.0.0.exe     <-- this is what you sell

No Windows PC handy? Push this folder to a GitHub repo -> Actions tab -> "Build Windows installer" -> Run.
Download the installer from the run's Artifacts. (Do NOT push SELLER_ONLY - .gitignore already excludes it.)

## 2. Rebrand (edit product.py only)
App name, version, publisher, support email, free-trial limit. Then rebuild.

## 3. Sell with license keys
Customers install the free trial (limit: 10 passwords). After they pay you:

    cd SELLER_ONLY
    python make_license.py "Customer Name" customer@email.com

Send them the printed `VLT1-...` key. They paste it in the app under "Activate" and it unlocks forever, offline.
Every key you issue is logged in SELLER_ONLY\issued_licenses.log.

**Keep SELLER_ONLY\private_key.pem secret and backed up.** Anyone with it can make keys, and if you lose it you
cannot issue keys that your released builds accept. Never put that folder in the installer or a public repo.

## 4. Before charging real money
- **Code signing certificate** (~$100-400/yr): unsigned installers trigger Windows SmartScreen "unknown publisher" warnings.
  Sign `VaultLite-Setup-x.y.z.exe` with signtool once you have one.
- Test the installer on a clean Windows 10/11 PC (or VM) before selling.
- Add a refund policy and a short Terms/Privacy page on your sales page. State clearly: data never leaves the PC and
  a forgotten master password cannot be recovered.
- Keys are not locked to one PC, so a buyer could share theirs. Typical for small software; machine-locking can be added later.

## How it is built
- Desktop window: pywebview (Edge WebView2). If it is missing, the app opens in the default browser and quits when the tab closes.
- Data: %APPDATA%\VaultLite (survives updates/uninstall). Vault key is derived from the master password (scrypt) and
  never stored on disk. Auto-locks after 15 minutes idle.
