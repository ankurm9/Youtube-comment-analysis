import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
import re
import emoji
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import matplotlib.pyplot as plt

load_dotenv()

def fetch_comments(youtube, video_id, uploader_channel_id, max_comments=600):
    print("Fetching Comments...")
    comments = []
    nextPageToken = None
    while len(comments) < max_comments:
        request = youtube.commentThreads().list(
            part='snippet',
            videoId=video_id,
            maxResults=100,
            pageToken=nextPageToken
        )
        response = request.execute()
        for item in response['items']:
            comment = item['snippet']['topLevelComment']['snippet']
            if comment['authorChannelId']['value'] != uploader_channel_id:
                comments.append(comment['textDisplay'])
        nextPageToken = response.get('nextPageToken')
        if not nextPageToken:
            break
    return comments

def filter_comments(comments, threshold_ratio=0.65):
    hyperlink_pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    relevant_comments = []

    for comment_text in comments:
        comment_text = comment_text.lower().strip()
        emojis = emoji.emoji_count(comment_text)
        text_characters = len(re.sub(r'\s', '', comment_text))

        if (any(char.isalnum() for char in comment_text)) and not hyperlink_pattern.search(comment_text):
            if emojis == 0 or (text_characters / (text_characters + emojis)) > threshold_ratio:
                relevant_comments.append(comment_text)

    return relevant_comments

def store_comments(comments, filename="ytcomments.txt"):
    with open(filename, 'w', encoding='utf-8') as f:
        for comment in comments:
            f.write(comment + "\n")
    print("Comments stored successfully!")

def analyze_sentiment(comments):
    def sentiment_scores(comment, polarity):
        sentiment_object = SentimentIntensityAnalyzer()
        sentiment_dict = sentiment_object.polarity_scores(comment)
        polarity.append(sentiment_dict['compound'])
        return polarity

    polarity = []
    positive_comments = []
    negative_comments = []
    neutral_comments = []

    for comment in comments:
        polarity = sentiment_scores(comment, polarity)
        if polarity[-1] > 0.05:
            positive_comments.append(comment)
        elif polarity[-1] < -0.05:
            negative_comments.append(comment)
        else:
            neutral_comments.append(comment)

    return polarity, positive_comments, negative_comments, neutral_comments

def extract_video_id(url):
    video_id = None
    patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            break
    return video_id

def main():
    API_KEY = os.getenv('API_KEY')
    youtube = build('youtube', 'v3', developerKey=API_KEY)

    video_url = input('Enter YouTube Video URL: ')
    video_id = extract_video_id(video_url)

    if not video_id:
        print("Invalid YouTube URL")
        return

    print("video id: " + video_id)

    video_response = youtube.videos().list(part='snippet', id=video_id).execute()

    if not video_response['items']:
        print("Video not found or invalid video ID.")
        return

    video_snippet = video_response['items'][0]['snippet']
    uploader_channel_id = video_snippet['channelId']
    print("channel id: " + uploader_channel_id)

    comments = fetch_comments(youtube, video_id, uploader_channel_id)
    print(comments[:5])

    relevant_comments = filter_comments(comments)
    print(relevant_comments[:5])

    store_comments(relevant_comments)

    polarity, positive_comments, negative_comments, neutral_comments = analyze_sentiment(relevant_comments)
    print("Polarity Scores:", polarity[:5])

    avg_polarity = sum(polarity) / len(polarity)
    print("Average Polarity:", avg_polarity)
    if avg_polarity > 0.05:
        print("The Video has got a Positive response")
    elif avg_polarity < -0.05:
        print("The Video has got a Negative response")
    else:
        print("The Video has got a Neutral response")

    positive_count = len(positive_comments)
    negative_count = len(negative_comments)
    neutral_count = len(neutral_comments)

    labels = ['Positive', 'Negative', 'Neutral']
    comment_counts = [positive_count, negative_count, neutral_count]

    plt.bar(labels, comment_counts, color=['blue', 'red', 'grey'])
    plt.xlabel('Sentiment')
    plt.ylabel('Comment Count')
    plt.title('Sentiment Analysis of Comments')
    plt.show()

    # # Creating pie chart
    # plt.figure(figsize=(10, 6))
    # plt.pie(comment_counts, labels=labels, autopct='%1.1f%%', startangle=140)
    # plt.axis('equal')
    # plt.show()

if __name__ == "__main__":
    main()
