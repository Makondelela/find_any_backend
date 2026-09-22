# FindFast Application Assistant extension

This extension fills job application forms in the user's real Chrome tab. It does not use the hosted headless assistant browser.

The extension includes PNG icons in `icons/` for the Chrome toolbar, extensions page, and store package.

## Install locally

1. Open `chrome://extensions` in Chrome.
2. Enable **Developer mode**.
3. Choose **Load unpacked**.
4. Select this `chrome_extension` directory.
5. Log in to FindFast in the same Chrome profile.
6. Open a job application page, click the extension icon, and choose **Fill current form**.

From FindFast, **View Job** keeps using the original hosted assistant. Use **Open in Chrome** when you want the application to open in a normal tab for this extension.

The default profile API is `https://find-any-backend-1.onrender.com/api/profile`. Use **Connection settings** in the popup to switch to `http://127.0.0.1:5000` during local development.

## How filling works

The content script inspects visible inputs, textareas, and selects. It combines labels, associated labels, placeholders, names, IDs, and nearby form text to identify fields. The service worker requests the authenticated user's profile and backend field mappings from FindFast, caches them locally for 2 hours, and sends only that data to the active tab. Use **Refresh profile** in the extension popup after changing your profile. Values are written with native input/change events so common form frameworks detect them.

Files that cannot be safely inferred, file uploads, CAPTCHA fields, and unknown controls are left untouched for review.
