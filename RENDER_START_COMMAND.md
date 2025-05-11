# Render Start Command

For the "Start Command" field in your Render deployment, enter:

```
bash start.sh
```

This will run the start.sh script which:
1. Installs NLTK data
2. Runs your main application (src/main.py)

## Important Note About Time Zones

The application has been updated to properly handle time zones. All times are now stored in Singapore Time (SGT) and displayed correctly in the user interface.

If you're experiencing any time zone issues after deployment:
1. Check the logs to ensure the application is starting correctly
2. Verify that the pytz package is installed correctly
3. Test the application by creating a new feeding/diaper/sleep record and confirming the displayed time is correct 