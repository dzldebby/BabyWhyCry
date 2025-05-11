# Timezone Fix for Baby Alert

This guide explains how to fix timezone issues in the Baby Alert application.

## The Issue

The application was previously storing times in UTC format but displaying them without proper timezone conversion. This caused times to appear in UTC instead of Singapore Time (SGT).

## The Fix

We've implemented several fixes:

1. **Enhanced `format_datetime` function**: Now properly converts all times to SGT and explicitly shows "(SGT)" in the displayed time.

2. **Updated model defaults**: Changed model definitions to use `get_sgt_now` instead of `datetime.utcnow`.

3. **Created a fix script**: `fix_timezone.py` updates all existing database records to have proper timezone information.

4. **Updated `start.sh`**: Now runs the timezone fix script before starting the application.

## How to Deploy with the Fix

1. Push all code changes to your repository.

2. Deploy to Render with the following settings:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `bash start.sh`

3. The `start.sh` script will:
   - Install NLTK data
   - Run the timezone fix script
   - Start the application

## Testing the Fix

After deployment, test the application by:

1. Creating a new feeding record
2. Verifying that the time displayed includes "(SGT)" and shows the correct Singapore time
3. Checking other time-related functions like sleep tracking and diaper changes

## Troubleshooting

If timezone issues persist:

1. Check the Render logs for any errors in the timezone fix script
2. Verify that the `pytz` package is installed correctly
3. Ensure that the database connection is working properly

If you need to manually run the fix script:

```bash
python fix_timezone.py
``` 