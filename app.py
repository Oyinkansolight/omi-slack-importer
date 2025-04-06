import os
import re
import json
import requests
from config import Config
from datetime import datetime
from slack_sdk import WebClient
from flask import Flask, render_template, redirect, url_for, session, request, jsonify, Response

app = Flask(__name__)
app.config.from_object(Config)

@app.route("/")
def index():
    # Get error message from query parameters if any
    error_message = request.args.get("error")
    
    if "slack_token" not in session:
        # Show login button if not authenticated
        auth_url = f"{app.config['SLACK_AUTH_URL']}?client_id={app.config['SLACK_CLIENT_ID']}&user_scope={app.config['SLACK_SCOPE']}&bot_scope={app.config['BOT_SCOPE']}&redirect_uri={app.config['SLACK_REDIRECT_URI']}"
        return render_template("index.html", auth_url=auth_url, authenticated=False, error_message=error_message)

    # Check if user has a valid user_id in session
    if "user_id" not in session:
        # Clear any existing session data
        session.clear()
        return redirect(url_for("index", error="Invalid session. Please authenticate through the correct Omi link."))

    # If authenticated, fetch and display channels
    client = WebClient(token=session["slack_token"])
    try:
        # Fetch conversations
        conversations = client.conversations_list(
            types="public_channel,private_channel,mpim,im"
        )

        # Fetch user info for DMs
        users_info = {}
        if conversations.get("channels"):
            for channel in conversations["channels"]:
                if channel["is_im"]:
                    users_info[channel["user"]] = client.users_info(
                        user=channel["user"]
                    )["user"]

        # Get the current user's ID
        current_user_id = session.get("slack_user_id")
        
        # Categorize channels
        categorized_channels = {
            "direct_messages": [],
            "group_chats": [],
            "public_channels": []
        }
        
        # Track channel usage frequency
        channel_usage = {}
        
        # Try to get channel usage from session, or initialize if not present
        if "channel_usage" not in session:
            session["channel_usage"] = {}
        
        # Process each channel
        for channel in conversations.get("channels", []):
            # Add user info to channel data
            if channel["is_im"]:
                user_id = channel["user"]
                if user_id in users_info:
                    channel["user_info"] = users_info[user_id]
                    channel["display_name"] = users_info[user_id].get("real_name") or users_info[user_id].get("name", "Unknown")
                else:
                    channel["display_name"] = "Unknown User"
                
                # Check if this is the user's own DM
                if user_id == current_user_id:
                    channel["is_own_dm"] = True
                    categorized_channels["direct_messages"].insert(0, channel)
                else:
                    channel["is_own_dm"] = False
                    categorized_channels["direct_messages"].append(channel)
            elif channel["is_mpim"]:
                categorized_channels["group_chats"].append(channel)
            else:
                categorized_channels["public_channels"].append(channel)
            
            # Get usage count from session
            channel_id = channel["id"]
            channel_usage[channel_id] = session["channel_usage"].get(channel_id, 0)
        
        # Sort channels by usage frequency
        for category in categorized_channels:
            categorized_channels[category] = sorted(
                categorized_channels[category],
                key=lambda x: channel_usage.get(x["id"], 0),
                reverse=True
            )
        
        return render_template(
            "index.html",
            authenticated=True,
            categorized_channels=categorized_channels,
            users_info=users_info,
            error_message=error_message
        )
    except Exception as e:
        # Handle token expiration or other errors
        print(f"Error fetching conversations: {e}")
        session.pop("slack_token", None)
        return redirect(url_for("index"))


@app.route("/auth")
def auth():
    """Initiate the OAuth flow"""
    # Get user ID from query parameter
    user_id = request.args.get("uid")
    
    # Check if this is the exact URL pattern we want (/auth?uid)
    if not user_id or len(request.args) > 1:
        # Redirect to index with error message
        return redirect(url_for("index", error="Invalid authentication URL. Please use the correct link from Omi."))

    # Store user ID in session and make session permanent
    session.permanent = True
    session["user_id"] = user_id
    # Force immediate session save
    session.modified = True
    # Regenerate session ID to prevent fixation
    try:
        session.regenerate()
    except AttributeError:
        # Fallback for environments without regenerate
        session.clear()
        session["user_id"] = user_id
        session.modified = True
    auth_url = f"{app.config['SLACK_AUTH_URL']}?client_id={app.config['SLACK_CLIENT_ID']}&user_scope={app.config['SLACK_SCOPE']}&bot_scope={app.config['BOT_SCOPE']}&redirect_uri={app.config['SLACK_REDIRECT_URI']}"
    return redirect(auth_url)


@app.route("/auth/callback")
def auth_callback():
    # Check if user_id exists in session
    if "user_id" not in session:
        return redirect(url_for("index", error="Invalid authentication flow. Please start from the Omi link."))
        
    code = request.args.get("code")
    if not code:
        return redirect(url_for("index"))

    # Exchange code for token
    data = {
        "client_id": app.config["SLACK_CLIENT_ID"],
        "client_secret": app.config["SLACK_CLIENT_SECRET"],
        "code": code,
        "redirect_uri": app.config["SLACK_REDIRECT_URI"],
    }
    response = requests.post(app.config["SLACK_TOKEN_URL"], data=data)

    if response.status_code == 200:
        auth_data = response.json()
        if auth_data.get("ok", False):
            session["slack_token"] = auth_data["authed_user"]["access_token"]
            session["slack_user_id"] = auth_data["authed_user"]["id"]
            return redirect(url_for("index"))

    # If OAuth fails
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.pop("slack_token", None)
    session.pop("slack_user_id", None)
    return redirect(url_for("index"))


@app.route("/fetch_messages/<channel_id>")
def fetch_messages(channel_id):
    if "slack_token" not in session:
        return jsonify({"error": "Not authenticated with Slack"}), 401

    if "user_id" not in session:
        return jsonify({"error": "Not authenticated Omi"}), 401

    user_id = session["user_id"]

    client = WebClient(token=session["slack_token"])
    try:
        # Fetch the last 90 messages from the channel with additional data
        result = client.conversations_history(
            channel=channel_id, 
            limit=150,
            include_all_metadata=True
        )

        messages = result.get("messages", [])

        # Format messages for Omi
        memories = format_slack_messages_to_memories(messages=messages, client=client)

        text = " and then, ".join([mem["content"] for mem in memories])

        if text == "":
            text = "No messages found"

        memory = {
            "memories": memories,
            "text_source": "other",
            "text": text,
        }

        # Send to Omi API with the correct endpoint
        omi_response = requests.post(
            f"{app.config.get('OMI_API_URL')}/integrations/{app.config.get('OMI_APP_ID')}/user/memories",
            json=memory,
            params={"uid": user_id},
            headers={
                "Authorization": f"Bearer {app.config.get('OMI_API_KEY')}",
                "ngrok-skip-browser-warning": "true"
            },
        )

        if omi_response.status_code == 200:
            return jsonify(
                {
                    "success": True,
                    "message": f"Successfully imported conversation to Omi",
                }
            )
        else:
            return (
                jsonify(
                    {
                        "error": "Failed to import messages to Omi",
                        "details": omi_response.json(),
                    }
                ),
                500,
            )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def format_slack_messages_to_memories(messages, client):
    """
    Process Slack messages and format them as memories.

    Args:
        messages (list): List of Slack message objects
        client: Slack client object with users_info method

    Returns:
        list: Formatted memories in the structure required
    """
    memories = []

    for msg in messages:
        if "text" in msg and "user" in msg:
            user_info = client.users_info(user=msg["user"])
            sender_username = user_info["user"]["name"]

            # Extract any @mentions from the text to identify who the message was directed to
            recipient = "the channel"  # Default if no direct mention
            text = msg["text"]

            # Check for @mentions in Slack format: <@USER_ID>
            mention_pattern = r"<@([A-Z0-9]+)>"
            mentions = re.findall(mention_pattern, text)

            if mentions:
                # Get the username for the first mentioned user
                try:
                    recipient_info = client.users_info(user=mentions[0])
                    recipient = recipient_info["user"]["name"]
                    # Clean up the mention formatting in the text
                    text = re.sub(mention_pattern, f"@{recipient}", text)
                except:
                    pass  # Keep default recipient if mention lookup fails

            # Handle media files in the message
            media_content = []
            
            # Check for files in the message
            if "files" in msg and msg["files"]:
                for file in msg["files"]:
                    file_type = file.get("filetype", "").lower()
                    file_url = file.get("url_private", "")
                    file_name = file.get("name", "unnamed file")
                    
                    if file_type in ["jpg", "jpeg", "png", "gif"]:
                        media_content.append(f"[Image: {file_name} - {file_url}]")
                    elif file_type in ["mp4", "mov", "avi"]:
                        media_content.append(f"[Video: {file_name} - {file_url}]")
                    elif file_type in ["mp3", "wav", "ogg"]:
                        media_content.append(f"[Audio: {file_name} - {file_url}]")
                    else:
                        media_content.append(f"[File: {file_name} - {file_url}]")
            
            # Check for images in the message (Slack's image blocks)
            if "blocks" in msg:
                for block in msg["blocks"]:
                    if block.get("type") == "image":
                        image_url = block.get("image_url", "")
                        alt_text = block.get("alt_text", "image")
                        media_content.append(f"[Image: {alt_text} - {image_url}]")
            
            # Add media content to the text if any
            if media_content:
                text += " " + " ".join(media_content)

            # Create memory entry in the required format
            memory_content = f"{sender_username} said to {recipient}: {text}"

            # Add to memories array with relevant tags
            memory_entry = {
                "content": memory_content,
                "tags": ["conversation", "slack"],
            }

            # Add additional tags based on content
            if "meeting" in text.lower() or "schedule" in text.lower():
                memory_entry["tags"].append("meetings")
            if "deadline" in text.lower() or "due" in text.lower():
                memory_entry["tags"].append("deadlines")
            if "question" in text.lower() or text.endswith("?"):
                memory_entry["tags"].append("questions")
            
            # Add media tags if media is present
            if media_content:
                memory_entry["tags"].append("media")
                if any("[Image:" in item for item in media_content):
                    memory_entry["tags"].append("images")
                if any("[Video:" in item for item in media_content):
                    memory_entry["tags"].append("videos")
                if any("[Audio:" in item for item in media_content):
                    memory_entry["tags"].append("audio")
                if any("[File:" in item for item in media_content):
                    memory_entry["tags"].append("files")

            memories.append(memory_entry)

    return memories


# Example usage:
# formatted_memories = format_slack_messages_to_memories(messages, slack_client)
# memory["memories"] = formatted_memories

@app.route("/consent", methods=["POST"])
def consent():
    session["consent_given"] = True
    return jsonify({"success": True})


@app.route("/fetch_media/<channel_id>")
def fetch_media(channel_id):
    if "slack_token" not in session:
        return jsonify({"error": "Not authenticated with Slack"}), 401

    client = WebClient(token=session["slack_token"])
    try:
        # Fetch the last 150 messages from the channel with additional data
        result = client.conversations_history(
            channel=channel_id, 
            limit=150,
            include_all_metadata=True
        )

        messages = result.get("messages", [])
        
        # Extract media files from messages
        media_files = []
        
        for msg in messages:
            # Check for files in the message
            if "files" in msg and msg["files"]:
                for file in msg["files"]:
                    file_type = file.get("filetype", "").lower()
                    file_url = file.get("url_private", "")
                    file_name = file.get("name", "unnamed file")
                    file_id = file.get("id", "")
                    
                    media_type = "file"
                    if file_type in ["jpg", "jpeg", "png", "gif"]:
                        media_type = "image"
                    elif file_type in ["mp4", "mov", "avi"]:
                        media_type = "video"
                    elif file_type in ["mp3", "wav", "ogg"]:
                        media_type = "audio"
                    
                    media_files.append({
                        "id": file_id,
                        "name": file_name,
                        "type": media_type,
                        "url": file_url,
                        "timestamp": msg.get("ts", "")
                    })
            
            # Check for images in the message (Slack's image blocks)
            if "blocks" in msg:
                for block in msg["blocks"]:
                    if block.get("type") == "image":
                        image_url = block.get("image_url", "")
                        alt_text = block.get("alt_text", "image")
                        block_id = block.get("block_id", "")
                        
                        media_files.append({
                            "id": block_id,
                            "name": alt_text,
                            "type": "image",
                            "url": image_url,
                            "timestamp": msg.get("ts", "")
                        })
        
        return jsonify({
            "success": True,
            "media_files": media_files
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/proxy_media")
def proxy_media():
    """Proxy media requests to Slack to handle authentication"""
    if "slack_token" not in session:
        return jsonify({"error": "Not authenticated with Slack"}), 401
    
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    
    try:
        # Use the Slack client to make the request with proper authentication
        client = WebClient(token=session["slack_token"])
        
        # Make a direct HTTP request to the URL with the token
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {session['slack_token']}"},
            stream=True
        )
        
        # Check if the request was successful
        if response.status_code == 200:
            # Get the content type from the response
            content_type = response.headers.get('Content-Type', 'application/octet-stream')
            
            # Return the media content with the appropriate content type
            return Response(
                response.iter_content(chunk_size=8192),
                content_type=content_type
            )
        else:
            return jsonify({"error": f"Failed to fetch media: {response.status_code}"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/track_channel_usage/<channel_id>", methods=["POST"])
def track_channel_usage(channel_id):
    """Track when a user interacts with a channel to sort by frequency of use"""
    if "slack_token" not in session:
        return jsonify({"error": "Not authenticated with Slack"}), 401
    
    try:
        # Initialize channel usage in session if not present
        if "channel_usage" not in session:
            session["channel_usage"] = {}
        
        # Increment usage count for this channel
        if channel_id in session["channel_usage"]:
            session["channel_usage"][channel_id] += 1
        else:
            session["channel_usage"][channel_id] = 1
        
        # Force session to save
        session.modified = True
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
