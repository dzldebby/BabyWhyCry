# Deploying Baby Alert to Render

This guide explains how to deploy the Baby Alert application to Render.com.

## Prerequisites

1. A Render.com account
2. A Supabase PostgreSQL database (already set up)
3. A Telegram Bot Token
4. An OpenAI API Key (for NLP capabilities)

## Deployment Steps

### 1. Fork or Clone the Repository

Ensure you have the latest version of the code in your own Git repository.

### 2. Create a New Web Service on Render

1. Log in to your Render account
2. Click "New +" and select "Web Service"
3. Connect your GitHub/GitLab repository
4. Select the repository containing the Baby Alert application

### 3. Configure the Web Service

Enter the following details:
- **Name**: baby-alert-bot (or your preferred name)
- **Environment**: Python
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `bash start.sh`

### 4. Set Environment Variables

Add the following environment variables:
- `TELEGRAM_BOT_TOKEN`: Your Telegram Bot token
- `DATABASE_URL`: Your Supabase PostgreSQL connection string (use the Connection Pooler URL for IPv4 compatibility)
- `OPENAI_API_KEY`: Your OpenAI API key

### 5. Deploy the Service

Click "Create Web Service" to start the deployment.

### 6. Monitor the Deployment

- Check the logs for any errors during deployment
- Verify that the application connects to the database
- Test the Telegram bot functionality

## Troubleshooting

### Database Connection Issues

- Ensure you're using the Supabase Connection Pooler URL, not the direct connection string
- Check if your IP is allowed in Supabase

### Bot Not Responding

- Verify your Telegram Bot Token
- Check if the application is running by reviewing the logs on Render

### NLP Functions Not Working

- Verify your OpenAI API Key
- Check the logs for any specific errors related to OpenAI API calls

## Scaling and Monitoring

Render provides built-in monitoring for your applications. You can:
- View logs in real-time
- Set up alerts
- Scale up your service as needed 