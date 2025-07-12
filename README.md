# Skill Swap Platform

A Flask-based web application that enables users to connect and exchange skills with each other. Users can create profiles showcasing their skills, search for others with complementary abilities, and request skill swaps.

## Features

### User Authentication
- Secure user registration and login
- Password hashing with Flask-Bcrypt
- Session management with Flask-Login

### Profile Management
- Create and edit user profiles
- Add skills offered and skills wanted
- Set availability preferences
- Toggle profile visibility (public/private)

### Skill Discovery
- Browse all public user profiles
- Search for users by skills or name
- View detailed user profiles
- Responsive Bootstrap card layout

### Swap Request System
- Send skill swap requests to other users
- Accept, reject, or delete requests
- Track request status (Pending/Accepted/Rejected)
- View sent and received requests dashboard

### Responsive Design
- Mobile-friendly Bootstrap 5 interface
- Dark theme support
- Intuitive navigation and user experience

## Technology Stack

- **Backend**: Flask, SQLAlchemy, Flask-Login, Flask-Bcrypt, Flask-WTF
- **Database**: SQLite
- **Frontend**: HTML5, Bootstrap 5, Font Awesome icons
- **Template Engine**: Jinja2

## Installation and Setup

1. **Clone the repository** (if applicable) or ensure all files are in your project directory

2. **Install dependencies**:
   ```bash
   pip install Flask Flask-SQLAlchemy Flask-Login Flask-Bcrypt Flask-WTF WTForms
   ```

3. **Set environment variables**:
   ```bash
   export SESSION_SECRET="your-secret-key-here"
   export DATABASE_URL="sqlite:///skillswap.db"
   ```

4. **Run the application**:
   ```bash
   python main.py
   ```

5. **Access the application**:
   Open your browser and navigate to `http://localhost:5000`

## Project Structure

