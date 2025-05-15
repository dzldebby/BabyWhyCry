# Quick Bottle Feeding Feature

The Quick Bottle feature allows parents to instantly start a bottle feeding session with a single tap from their phone's home screen, significantly reducing the number of steps required to log a feeding.

## How It Works

This feature uses Telegram's deep linking capabilities to immediately start a bottle feeding session when you open the bot through a special link.

## Ways to Use Quick Bottle Feeding

### 1. Direct Command
Simply type `/quick_bottle` in the chat with the bot, and a bottle feeding session will start immediately for your selected baby.

### 2. Deep Link
Use this link to start a bottle feeding session directly:
```
https://t.me/your_bot_username?start=quick_bottle
```
(Replace `your_bot_username` with your actual bot's username)

## First Time Setup

The first time you use the Quick Bottle feature:

1. If you have only one baby registered, that baby will be automatically selected
2. If you have multiple babies, you'll see a special selection menu to choose which baby to feed
3. After selecting a baby, the bottle feeding will start immediately
4. For subsequent uses, the system will remember your selection

## Ending a Feeding Session

You have two ways to end a feeding session:

1. Tap the "Done Feeding" button that appears after starting a feeding
2. Type `/done` in the chat

After ending a bottle feeding, you'll be prompted to enter the amount, making the process quick and efficient.

## Setting Up Home Screen Shortcuts

### Android Instructions
1. Install a shortcut creator app from Google Play Store (like "Shortcut Maker")
2. Create a new shortcut pointing to: `https://t.me/your_bot_username?start=quick_bottle`
3. Choose an icon (like a baby bottle)
4. Place the shortcut on your home screen

### iPhone/iOS Instructions
1. Open Safari
2. Navigate to `https://t.me/your_bot_username?start=quick_bottle`
3. Tap the Share button (box with arrow)
4. Select "Add to Home Screen"
5. Name it "Quick Bottle" or something similar
6. Tap "Add"

## Usage Notes

- The default feeding type is set to bottle
- For night feedings, you can complete the entire process with just two taps:
  1. Tap the shortcut on your home screen to start feeding
  2. Tap "Done Feeding" when finished (or type `/done`)

## Benefits

- Significantly reduces the number of steps to log a feeding
- Perfect for middle-of-the-night feedings when you want minimal interaction
- Helps ensure accurate tracking even when you're tired or busy
- No need to navigate through multiple menus 