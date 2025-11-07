# Fantasy Football Dashboard

A beautiful Streamlit web application for viewing and comparing data from both Sleeper and Yahoo Fantasy Football leagues.

## Features

- 📊 **Sleeper Integration**: View league standings, matchups, rosters, and league settings
- 🏈 **Yahoo Integration**: Connect to Yahoo Fantasy Football leagues (requires OAuth)
- 📈 **Side-by-Side Comparison**: View data from both platforms simultaneously
- 🎨 **Modern UI**: Clean, responsive interface built with Streamlit

## Setup

### Prerequisites

- Python 3.8 or higher
- Sleeper league ID: `1257479697114075136`
- Yahoo league ID: `572651`

### Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. For Yahoo Fantasy integration, you'll need to:
   - Create a Yahoo Developer App at https://developer.yahoo.com/apps/
   - Get your Consumer Key and Consumer Secret
   - Use the OAuth flow in the app sidebar to authenticate

### Running the App

1. Navigate to the app directory:
```bash
cd fantasy_football_ui
```

2. Run Streamlit:
```bash
streamlit run app.py
```

3. The app will open in your browser at `http://localhost:8501`

## Sharing Your App

### Option 1: Streamlit Cloud (Recommended)

1. Push your code to GitHub
2. Go to https://share.streamlit.io/
3. Sign in with GitHub
4. Deploy your app by connecting your repository
5. Share the public URL with others!

### Option 2: Local Network Sharing

1. Run Streamlit with network access:
```bash
streamlit run app.py --server.address 0.0.0.0
```

2. Share your local IP address (others on your network can access it)

### Option 3: Self-Hosted Server

Deploy to any server that supports Python:
- Heroku
- AWS EC2
- DigitalOcean
- Google Cloud Platform

## Usage

1. **Select Platform**: Choose between Sleeper, Yahoo, or Both in the sidebar
2. **Yahoo Authentication**: If using Yahoo, enter your Consumer Key and Secret in the sidebar, then follow the OAuth flow
3. **View Data**: Navigate through different tabs to see:
   - League Standings
   - Weekly Matchups
   - Team Rosters
   - League Settings

## Configuration

League IDs are currently hardcoded in `app.py`:
- Sleeper League ID: `1257479697114075136`
- Yahoo League ID: `572651`

To change these, edit the constants at the top of the `main()` function in `app.py`.

## Notes

- Sleeper API is public and doesn't require authentication
- Yahoo API requires OAuth 1.0 authentication
- Yahoo league keys follow the format: `{game_key}.l.{league_id}` (e.g., `414.l.572651`)

## Troubleshooting

- **Yahoo Authentication Issues**: Make sure your Consumer Key and Secret are correct, and that you've authorized the app in Yahoo
- **League Not Found**: Verify your league IDs are correct and the leagues are accessible
- **API Errors**: Check your internet connection and that the APIs are accessible

## License

This project is open source and available for personal use.

