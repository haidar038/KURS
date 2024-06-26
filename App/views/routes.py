from flask import Blueprint, current_app, request, render_template, flash, redirect, url_for, jsonify, session, send_file
from flask_login import login_required, current_user
from flask_sqlalchemy import pagination
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import asc
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import json, requests, secrets, os

# from models import User, DataPangan, Kelurahan

views = Blueprint('views', __name__)

# MANIFEST
@views.route('/manifest.json')
def serve_manifest():
    return send_file('manifest.json', mimetype='application/manifest+json')

@views.route('/sw.js')
def serve_sw():
    return send_file('sw.js', mimetype='application/javascript')

# MAIN ROUTES

@views.route('/')
def index():
    data_tps = [
        {"id": 1, "nama": "TPS Gambesi", "latitude": "0.7552107801638247", "longitude": "127.33604266194835"},
        # Tambahkan data TPS lainnya dengan ID unik
    ]

    return render_template('index.html', data_tps=data_tps)