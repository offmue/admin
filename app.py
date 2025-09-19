#!/usr/bin/env python3
"""
NFL PickEm 2025/2026 - ULTIMATE FINAL VERSION
"""

import os
import sqlite3
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, session
import pytz

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Vienna timezone
VIENNA_TZ = pytz.timezone('Europe/Vienna')

# Valid users (simple login)
VALID_USERS = {
    1: 'Manuel',
    2: 'Daniel', 
    3: 'Raff',
    4: 'Haunschi'
}

# Admin users (can set results)
ADMIN_USERS = {'Manuel'}

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'nfl_pickem_ultimate_final')

# Database path
DB_PATH = 'nfl_pickem.db'

def init_db():
    """Initialize database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            abbreviation TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY,
            away_team_id INTEGER,
            home_team_id INTEGER,
            week INTEGER,
            game_time TEXT,
            is_completed INTEGER DEFAULT 0,
            away_score INTEGER,
            home_score INTEGER,
            FOREIGN KEY (away_team_id) REFERENCES teams (id),
            FOREIGN KEY (home_team_id) REFERENCES teams (id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS picks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            match_id INTEGER,
            team_id INTEGER,
            week INTEGER,
            is_correct INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (match_id) REFERENCES matches (id),
            FOREIGN KEY (team_id) REFERENCES teams (id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historical_picks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            team_id INTEGER,
            week INTEGER,
            is_correct INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (team_id) REFERENCES teams (id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS team_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            team_id INTEGER,
            usage_type TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (team_id) REFERENCES teams (id)
        )
    """)
    
    # Insert users
    for user_id, username in VALID_USERS.items():
        cursor.execute("INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)", (user_id, username))
    
    # Insert teams
    teams = [
        (1, 'Arizona Cardinals', 'ARI'), (2, 'Atlanta Falcons', 'ATL'), (3, 'Baltimore Ravens', 'BAL'),
        (4, 'Buffalo Bills', 'BUF'), (5, 'Carolina Panthers', 'CAR'), (6, 'Chicago Bears', 'CHI'),
        (7, 'Cincinnati Bengals', 'CIN'), (8, 'Cleveland Browns', 'CLE'), (9, 'Dallas Cowboys', 'DAL'),
        (10, 'Denver Broncos', 'DEN'), (11, 'Detroit Lions', 'DET'), (12, 'Green Bay Packers', 'GB'),
        (13, 'Houston Texans', 'HOU'), (14, 'Indianapolis Colts', 'IND'), (15, 'Jacksonville Jaguars', 'JAX'),
        (16, 'Kansas City Chiefs', 'KC'), (17, 'Las Vegas Raiders', 'LV'), (18, 'Los Angeles Chargers', 'LAC'),
        (19, 'Los Angeles Rams', 'LAR'), (20, 'Miami Dolphins', 'MIA'), (21, 'Minnesota Vikings', 'MIN'),
        (22, 'New England Patriots', 'NE'), (23, 'New Orleans Saints', 'NO'), (24, 'New York Giants', 'NYG'),
        (25, 'New York Jets', 'NYJ'), (26, 'Philadelphia Eagles', 'PHI'), (27, 'Pittsburgh Steelers', 'PIT'),
        (28, 'San Francisco 49ers', 'SF'), (29, 'Seattle Seahawks', 'SEA'), (30, 'Tampa Bay Buccaneers', 'TB'),
        (31, 'Tennessee Titans', 'TEN'), (32, 'Washington Commanders', 'WAS')
    ]
    
    for team_id, name, abbr in teams:
        cursor.execute("INSERT OR IGNORE INTO teams (id, name, abbreviation) VALUES (?, ?, ?)", (team_id, name, abbr))
    
    # Insert real NFL schedule (sample for W1-W3)
    matches = [
        # Week 1
        (1, 9, 26, 1, "2025-09-04 20:20:00"),  # Cowboys @ Eagles
        (2, 16, 18, 1, "2025-09-05 21:00:00"), # Chiefs vs Chargers
        (3, 30, 2, 1, "2025-09-07 13:00:00"),  # Buccaneers @ Falcons
        (4, 7, 8, 1, "2025-09-07 13:00:00"),   # Bengals @ Browns
        (5, 20, 14, 1, "2025-09-07 13:00:00"), # Dolphins @ Colts
        # Week 2
        (6, 32, 12, 2, "2025-09-11 20:15:00"), # Commanders @ Packers
        (7, 8, 3, 2, "2025-09-14 13:00:00"),   # Browns @ Ravens
        (8, 15, 7, 2, "2025-09-14 13:00:00"),  # Jaguars @ Bengals
        (9, 24, 9, 2, "2025-09-14 13:00:00"),  # Giants @ Cowboys
        (10, 6, 11, 2, "2025-09-14 13:00:00"), # Bears @ Lions
        # Week 3
        (11, 20, 4, 3, "2025-09-18 20:15:00"), # Dolphins @ Bills
        (12, 2, 5, 3, "2025-09-21 13:00:00"),  # Falcons @ Panthers
        (13, 12, 8, 3, "2025-09-21 13:00:00"), # Packers @ Browns
        (14, 13, 15, 3, "2025-09-21 13:00:00"), # Texans @ Jaguars
        (15, 9, 6, 3, "2025-09-21 16:25:00"),  # Cowboys @ Bears
    ]
    
    for match_id, away_id, home_id, week, game_time in matches:
        cursor.execute("""
            INSERT OR REPLACE INTO matches (id, away_team_id, home_team_id, week, game_time, is_completed)
            VALUES (?, ?, ?, ?, ?, 0)
        """, (match_id, away_id, home_id, week, game_time))
    
    # Insert historical data (CORRECTED)
    historical_data = [
        # Manuel: W1 Falcons (lost), W2 Cowboys (won) = 1 point
        (1, 2, 1, 0),   # Manuel, Falcons, W1, lost
        (1, 9, 2, 1),   # Manuel, Cowboys, W2, won
        
        # Daniel: W1 Broncos (won), W2 Eagles (won) = 2 points  
        (2, 10, 1, 1),  # Daniel, Broncos, W1, won
        (2, 26, 2, 1),  # Daniel, Eagles, W2, won
        
        # Raff: W1 Bengals (won), W2 Cowboys (won) = 2 points
        (3, 7, 1, 1),   # Raff, Bengals, W1, won
        (3, 9, 2, 1),   # Raff, Cowboys, W2, won
        
        # Haunschi: W1 Commanders (won), W2 Bills (won) = 2 points
        (4, 32, 1, 1),  # Haunschi, Commanders, W1, won
        (4, 4, 2, 1),   # Haunschi, Bills, W2, won
    ]
    
    for user_id, team_id, week, is_correct in historical_data:
        cursor.execute("""
            INSERT OR REPLACE INTO historical_picks (user_id, team_id, week, is_correct)
            VALUES (?, ?, ?, ?)
        """, (user_id, team_id, week, is_correct))
    
    # Insert team usage (CORRECTED)
    team_usage_data = [
        # Manuel: Falcons as loser, Cowboys as winner
        (1, 2, 'loser'),   # Manuel, Falcons, loser
        (1, 9, 'winner'),  # Manuel, Cowboys, winner
        
        # Daniel: Both as winners
        (2, 10, 'winner'), # Daniel, Broncos, winner
        (2, 26, 'winner'), # Daniel, Eagles, winner
        
        # Raff: Both as winners  
        (3, 7, 'winner'),  # Raff, Bengals, winner
        (3, 9, 'winner'),  # Raff, Cowboys, winner
        
        # Haunschi: Both as winners
        (4, 32, 'winner'), # Haunschi, Commanders, winner
        (4, 4, 'winner'),  # Haunschi, Bills, winner
    ]
    
    for user_id, team_id, usage_type in team_usage_data:
        cursor.execute("""
            INSERT OR REPLACE INTO team_usage (user_id, team_id, usage_type)
            VALUES (?, ?, ?)
        """, (user_id, team_id, usage_type))
    
    conn.commit()
    conn.close()
    print("Database initialized with real NFL schedule and historical data")

# Initialize database on startup
init_db()

@app.route('/')
def index():
    if 'user_id' not in session:
        return render_template('index.html', logged_in=False, valid_users=list(VALID_USERS.values()))
    
    is_admin = session.get('username') in ADMIN_USERS
    return render_template('index.html', logged_in=True, username=session['username'], is_admin=is_admin)

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        
        if not username:
            return jsonify({'success': False, 'message': 'Benutzername erforderlich'}), 400
        
        user_id = None
        for uid, uname in VALID_USERS.items():
            if uname == username:
                user_id = uid
                break
        
        if user_id:
            session['user_id'] = user_id
            session['username'] = username
            is_admin = username in ADMIN_USERS
            return jsonify({'success': True, 'message': f'Willkommen, {username}!', 'is_admin': is_admin})
        else:
            return jsonify({'success': False, 'message': 'Ungültiger Benutzername'}), 401
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'success': False, 'message': 'Server-Fehler beim Login'}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Erfolgreich abgemeldet'})

@app.route('/api/current-week')
def get_current_week_api():
    """API endpoint to get current week"""
    try:
        # Simple logic for current week
        return jsonify({'success': True, 'current_week': 3})
    except Exception as e:
        logger.error(f"Error getting current week: {e}")
        return jsonify({'success': False, 'current_week': 3}), 500

@app.route('/api/dashboard')
def dashboard():
    """Dashboard API with correct historical data"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Nicht angemeldet'}), 401
        
        user_id = session['user_id']
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get historical picks
        cursor.execute("SELECT is_correct FROM historical_picks WHERE user_id = ?", (user_id,))
        historical_picks = cursor.fetchall()
        historical_points = sum(1 for pick in historical_picks if pick[0])
        
        # Get current season picks
        cursor.execute("SELECT is_correct FROM picks WHERE user_id = ? AND is_correct IS NOT NULL", (user_id,))
        current_picks = cursor.fetchall()
        current_points = sum(1 for pick in current_picks if pick[0])
        
        total_points = historical_points + current_points
        total_picks = len(historical_picks) + len(current_picks)
        
        # Get team usage (CORRECTED)
        cursor.execute("""
            SELECT t.name, 
                   CASE WHEN hp.is_correct = 1 THEN 'winner' ELSE 'loser' END as usage_type
            FROM historical_picks hp 
            JOIN teams t ON hp.team_id = t.id 
            WHERE hp.user_id = ?
        """, (user_id,))
        historical_usage = cursor.fetchall()
        
        cursor.execute("""
            SELECT t.name, tu.usage_type 
            FROM team_usage tu 
            JOIN teams t ON tu.team_id = t.id 
            WHERE tu.user_id = ?
        """, (user_id,))
        current_usage = cursor.fetchall()
        
        # Combine both
        team_usage = historical_usage + current_usage
        
        winner_teams = [row[0] for row in team_usage if row[1] == 'winner']
        loser_teams = [row[0] for row in team_usage if row[1] == 'loser']
        
        # Calculate rank
        cursor.execute("""
            SELECT u.id, u.username, 
                   (COUNT(CASE WHEN hp.is_correct = 1 THEN 1 END) + 
                    COUNT(CASE WHEN p.is_correct = 1 THEN 1 END)) as total_points
            FROM users u
            LEFT JOIN historical_picks hp ON u.id = hp.user_id
            LEFT JOIN picks p ON u.id = p.user_id AND p.is_correct IS NOT NULL
            GROUP BY u.id, u.username
            ORDER BY total_points DESC
        """)
        rankings = cursor.fetchall()
        
        current_rank = 1
        for i, (uid, uname, points) in enumerate(rankings):
            if uid == user_id:
                current_rank = i + 1
                break
        
        conn.close()
        
        return jsonify({
            'success': True,
            'current_week': 3,
            'total_points': total_points,
            'correct_picks': f"{total_points}/{total_picks}" if total_picks > 0 else "0/0",
            'current_rank': current_rank,
            'winner_teams': winner_teams,
            'loser_teams': loser_teams
        })
        
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return jsonify({'success': False, 'message': 'Fehler beim Laden des Dashboards'}), 500

@app.route('/api/matches/<int:week>')
def get_matches(week):
    """Get matches for a specific week"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Nicht angemeldet'}), 401
        
        user_id = session['user_id']
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get matches for the week
        cursor.execute("""
            SELECT m.id, m.week, m.away_team_id, m.home_team_id, m.game_time, m.is_completed,
                   away_team.name as away_name, away_team.abbreviation as away_abbr,
                   home_team.name as home_name, home_team.abbreviation as home_abbr
            FROM matches m
            JOIN teams away_team ON m.away_team_id = away_team.id
            JOIN teams home_team ON m.home_team_id = home_team.id
            WHERE m.week = ?
            ORDER BY m.game_time
        """, (week,))
        
        matches_raw = cursor.fetchall()
        
        # Get user's picks for this week
        cursor.execute("SELECT match_id, team_id FROM picks WHERE user_id = ? AND week = ?", (user_id, week))
        user_picks = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Format matches for frontend
        matches_data = []
        for match in matches_raw:
            match_id, match_week, away_id, home_id, game_time, is_completed, away_name, away_abbr, home_name, home_abbr = match
            
            # Convert game time to Vienna timezone
            try:
                game_dt = datetime.fromisoformat(game_time)
                if game_dt.tzinfo is None:
                    game_dt = VIENNA_TZ.localize(game_dt)
                vienna_time = game_dt.astimezone(VIENNA_TZ)
                formatted_time = vienna_time.strftime("%d.%m.%Y, %H:%M")
            except:
                formatted_time = game_time
            
            matches_data.append({
                'id': match_id,
                'week': match_week,
                'away_team': {
                    'id': away_id,
                    'name': away_name,
                    'abbr': away_abbr,
                    'logo_url': f"https://a.espncdn.com/i/teamlogos/nfl/500/{away_abbr.lower()}.png"
                },
                'home_team': {
                    'id': home_id,
                    'name': home_name,
                    'abbr': home_abbr,
                    'logo_url': f"https://a.espncdn.com/i/teamlogos/nfl/500/{home_abbr.lower()}.png"
                },
                'game_time': formatted_time,
                'is_completed': bool(is_completed)
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'matches': matches_data,
            'picks': user_picks,
            'unpickable_teams': [],
            'unpickable_reasons': {}
        })
        
    except Exception as e:
        logger.error(f"Error getting matches for week {week}: {e}")
        return jsonify({'success': False, 'message': 'Fehler beim Laden der Spiele'}), 500

@app.route('/api/picks', methods=['POST'])
def save_pick():
    """Save a user's pick"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Nicht angemeldet'}), 401
        
        data = request.get_json()
        user_id = session['user_id']
        match_id = data.get('match_id')
        team_id = data.get('team_id')
        week = data.get('week')
        
        if not all([match_id, team_id, week]):
            return jsonify({'success': False, 'message': 'Unvollständige Daten'}), 400
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Save or update pick
        cursor.execute("""
            INSERT OR REPLACE INTO picks (user_id, match_id, team_id, week, is_correct)
            VALUES (?, ?, ?, ?, NULL)
        """, (user_id, match_id, team_id, week))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Pick gespeichert'})
        
    except Exception as e:
        logger.error(f"Error saving pick: {e}")
        return jsonify({'success': False, 'message': 'Fehler beim Speichern des Picks'}), 500

@app.route('/api/leaderboard')
def leaderboard():
    """Get leaderboard data"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT u.username, 
                   (COUNT(CASE WHEN hp.is_correct = 1 THEN 1 END) + 
                    COUNT(CASE WHEN p.is_correct = 1 THEN 1 END)) as total_points
            FROM users u
            LEFT JOIN historical_picks hp ON u.id = hp.user_id
            LEFT JOIN picks p ON u.id = p.user_id AND p.is_correct IS NOT NULL
            GROUP BY u.id, u.username
            ORDER BY total_points DESC
        """)
        
        results = cursor.fetchall()
        conn.close()
        
        leaderboard_data = []
        current_rank = 1
        prev_points = None
        
        for i, (username, points) in enumerate(results):
            if prev_points is not None and points < prev_points:
                current_rank = i + 1
            
            leaderboard_data.append({
                'rank': current_rank,
                'username': username,
                'points': points
            })
            prev_points = points
        
        return jsonify({'success': True, 'leaderboard': leaderboard_data})
        
    except Exception as e:
        logger.error(f"Leaderboard error: {e}")
        return jsonify({'success': False, 'message': 'Fehler beim Laden des Leaderboards'}), 500

@app.route('/api/all-picks')
def all_picks():
    """Get all users' picks"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get historical picks
        cursor.execute("""
            SELECT u.username, t.name, hp.week, hp.is_correct
            FROM historical_picks hp
            JOIN users u ON hp.user_id = u.id
            JOIN teams t ON hp.team_id = t.id
            ORDER BY hp.week, u.username
        """)
        
        historical_picks = cursor.fetchall()
        
        # Get current picks
        cursor.execute("""
            SELECT u.username, t.name, p.week, p.is_correct
            FROM picks p
            JOIN users u ON p.user_id = u.id
            JOIN teams t ON p.team_id = t.id
            WHERE p.is_correct IS NOT NULL
            ORDER BY p.week, u.username
        """)
        
        current_picks = cursor.fetchall()
        conn.close()
        
        # Combine and format
        all_picks_data = {}
        
        for username, team_name, week, is_correct in historical_picks + current_picks:
            if username not in all_picks_data:
                all_picks_data[username] = []
            
            all_picks_data[username].append({
                'team': team_name,
                'week': week,
                'is_correct': bool(is_correct) if is_correct is not None else None
            })
        
        return jsonify({'success': True, 'all_picks': all_picks_data})
        
    except Exception as e:
        logger.error(f"All picks error: {e}")
        return jsonify({'success': False, 'message': 'Fehler beim Laden der Picks'}), 500

@app.route('/api/pending-games')
def pending_games():
    """Get pending games for admin panel"""
    try:
        if 'user_id' not in session or session.get('username') not in ADMIN_USERS:
            return jsonify({'success': False, 'message': 'Keine Berechtigung'}), 403
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT m.id, m.week, 
                   away_team.name as away_name,
                   home_team.name as home_name,
                   m.game_time
            FROM matches m
            JOIN teams away_team ON m.away_team_id = away_team.id
            JOIN teams home_team ON m.home_team_id = home_team.id
            WHERE m.is_completed = 0
            ORDER BY m.week, m.game_time
        """)
        
        games = cursor.fetchall()
        conn.close()
        
        games_data = []
        for game_id, week, away_name, home_name, game_time in games:
            games_data.append({
                'id': game_id,
                'week': week,
                'description': f"W{week}: {away_name} @ {home_name}",
                'away_team': away_name,
                'home_team': home_name,
                'game_time': game_time
            })
        
        return jsonify({'success': True, 'games': games_data})
        
    except Exception as e:
        logger.error(f"Pending games error: {e}")
        return jsonify({'success': False, 'message': 'Fehler beim Laden der Spiele'}), 500

@app.route('/api/set-result', methods=['POST'])
def set_game_result():
    """Set game result and automatically validate picks"""
    try:
        if 'user_id' not in session or session.get('username') not in ADMIN_USERS:
            return jsonify({'success': False, 'message': 'Keine Berechtigung'}), 403
        
        data = request.get_json()
        game_id = data.get('game_id')
        away_score = data.get('away_score')
        home_score = data.get('home_score')
        
        if not all([game_id is not None, away_score is not None, home_score is not None]):
            return jsonify({'success': False, 'message': 'Unvollständige Daten'}), 400
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get game info
        cursor.execute("""
            SELECT away_team_id, home_team_id, week
            FROM matches 
            WHERE id = ?
        """, (game_id,))
        
        game_info = cursor.fetchone()
        if not game_info:
            return jsonify({'success': False, 'message': 'Spiel nicht gefunden'}), 404
        
        away_team_id, home_team_id, week = game_info
        
        # Determine winner
        if away_score > home_score:
            winner_team_id = away_team_id
        elif home_score > away_score:
            winner_team_id = home_team_id
        else:
            # Tie - no winner
            winner_team_id = None
        
        # Update game result
        cursor.execute("""
            UPDATE matches 
            SET away_score = ?, home_score = ?, is_completed = 1
            WHERE id = ?
        """, (away_score, home_score, game_id))
        
        # Validate all picks for this game
        cursor.execute("""
            SELECT id, user_id, team_id
            FROM picks 
            WHERE match_id = ?
        """, (game_id,))
        
        picks = cursor.fetchall()
        validated_picks = 0
        
        for pick_id, user_id, team_id in picks:
            is_correct = 1 if team_id == winner_team_id else 0
            
            cursor.execute("""
                UPDATE picks 
                SET is_correct = ?
                WHERE id = ?
            """, (is_correct, pick_id))
            
            # Update team usage
            usage_type = 'winner' if is_correct else 'loser'
            cursor.execute("""
                INSERT OR REPLACE INTO team_usage (user_id, team_id, usage_type)
                VALUES (?, ?, ?)
            """, (user_id, team_id, usage_type))
            
            validated_picks += 1
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': f'Ergebnis gesetzt und {validated_picks} Picks automatisch validiert'
        })
        
    except Exception as e:
        logger.error(f"Set result error: {e}")
        return jsonify({'success': False, 'message': 'Fehler beim Setzen des Ergebnisses'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
