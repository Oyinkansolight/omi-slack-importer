# Slack to Omi Importer

A Flask-based web application that allows users to import their Slack conversations and media files into Omi's memory system. This application provides a modern UI with features for previewing and importing Slack content.

## Features

- **Slack Authentication**: Secure OAuth-based authentication with Slack
- **Channel Browsing**: View all accessible Slack channels (public, private, and DMs)
- **Channel Categorization**: Channels are organized by type (User Chats, Group Chats, Direct Messages) and sorted by usage frequency
- **Media Preview**: Preview images, videos, and other media files from Slack channels
- **Memory Import**: Import conversations as memories to Omi's API
- **User Consent**: Built-in consent mechanism for data usage
- **Responsive Design**: Modern UI that works on desktop and mobile devices
- **Error Handling**: Graceful handling of API errors and network issues

## Requirements

- Python 3.8+
- Flask
- Slack SDK
- Requests

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/Oyinkansolight/omi-slack-importer.git
   cd omi-slack-importer
   ```

2. Create a virtual environment (optional but recommended):
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root with the following variables:
   ```
   OMI_APP_ID=your_omi_app_id
   OMI_API_KEY=your_omi_api_key
   OMI_API_URL=https://api.omi.ai
   SECRET_KEY=your_random_secret_key (for Flask session management)
   SLACK_CLIENT_ID=your_slack_client_id
   SLACK_CLIENT_SECRET=your_slack_client_secret
   SLACK_REDIRECT_URI=http://localhost:5000/auth/callback
   ```

## Slack App Configuration

1. Create a new Slack app at https://api.slack.com/apps
2. Configure the following OAuth scopes:
   - `channels:history`
   - `channels:read`
   - `groups:history`
   - `groups:read`
   - `im:history`
   - `im:read`
   - `mpim:history`
   - `mpim:read`
   - `users:read`
   - `files:read`
3. Set the Redirect URL to match your `SLACK_REDIRECT_URI` in the `.env` file
4. Install the app to your workspace and copy the Client ID and Client Secret to your `.env` file

## Running the Application

1. Start the Flask server:
   ```
   python app.py
   ```

2. Access the application in your browser:
   ```
   http://localhost:5000 or http://127.0.0.1:5000
   ```

3. For external access (e.g., for Omi integration), you can use ngrok:
   ```
   ngrok http http://localhost:5000 or ngrok http http://127.0.0.1:5000
   ```

## Usage

1. Click "Sign in with Slack" to authenticate with your Slack workspace
2. Accept the data usage consent
3. Browse your Slack channels, organized by type and usage frequency
4. Use the "Preview" button to view media files in a channel
5. Use the "Import" button to import conversations to Omi
6. Your channel usage is automatically tracked to provide better organization

## Architecture

- **Frontend**: HTML, CSS, JavaScript with Bootstrap 5
- **Backend**: Flask with Python
- **Authentication**: Slack OAuth
- **API Integration**: Slack API and Omi API

## Error Handling

The application includes comprehensive error handling:
- Authentication errors
- API request failures
- Media loading issues with fallback to error images
- Network timeouts

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 