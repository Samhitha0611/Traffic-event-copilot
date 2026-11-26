"""
High-impact Gemini-style Command Center Theme for Traffic Event Co-Pilot.
- Crisp Police Navy gradient hero + glowing live AI status dot
- Elevated suggestion cards with hover glow
- Hides default Streamlit chrome (sidebar, Deploy/menu) for demo polish
- Auto light/dark support
"""
from __future__ import annotations

import streamlit as st


def inject_css() -> None:
    """Inject polished, demo-ready Gemini-style AI CSS."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }

        /* Hide default Streamlit sidebar & fixed top header bar so nothing overlaps our navbar */
        section[data-testid="stSidebar"],
        [data-testid="collapsedControl"],
        [data-testid="stToolbar"],
        header[data-testid="stHeader"],
        #MainMenu {
            display: none !important;
        }
        .block-container {
            padding-top: 2rem !important;
            max-width: 1280px !important;
        }

        /* Subtle ambient background in light mode */
        .stApp {
            background: radial-gradient(circle at 50% 0%, #eef4ff 0%, #f8fafc 45%, #ffffff 100%);
        }

        /* Top-notch Gemini-style Hero Card */
        .gemini-hero {
            text-align: center;
            padding: 2rem 1.5rem 1.8rem 1.5rem;
            margin: 0.5rem auto 1.4rem auto;
            border-radius: 22px;
            background: radial-gradient(circle at 30% 20%, #1e3a8a 0%, #0b1b48 55%, #060d24 100%);
            color: #ffffff !important;
            box-shadow: 0 18px 45px rgba(7, 20, 60, 0.25), inset 0 1px 0 rgba(255,255,255,0.12);
            border: 1px solid rgba(96, 165, 250, 0.28);
        }
        .gemini-hero-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            background: rgba(59, 130, 246, 0.22);
            color: #93c5fd;
            padding: 0.3rem 0.95rem;
            border-radius: 999px;
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0.06em;
            border: 1px solid rgba(147, 197, 253, 0.3);
            margin-bottom: 0.9rem;
        }
        .live-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #34d399;
            box-shadow: 0 0 8px #34d399;
            display: inline-block;
            animation: pulseDot 1.8s infinite;
        }
        @keyframes pulseDot {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(1.25); }
        }
        .gemini-hero h1 {
            color: #ffffff !important;
            font-size: 2.35rem !important;
            font-weight: 700 !important;
            margin: 0 !important;
            letter-spacing: -0.02em;
            background: linear-gradient(90deg, #ffffff 0%, #bfdbfe 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .gemini-hero p {
            color: rgba(226, 232, 240, 0.85) !important;
            font-size: 0.98rem !important;
            margin: 0.5rem auto 0 auto !important;
            max-width: 580px;
        }

        /* 4-Step Visual Progress Stepper */
        .stepper-row {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 0.5rem;
            flex-wrap: wrap;
            margin: 0 0 1.1rem 0;
        }
        .step-pill {
            padding: 0.32rem 0.85rem;
            border-radius: 999px;
            font-size: 0.8rem;
            font-weight: 600;
            border: 1px solid rgba(148, 163, 184, 0.35);
            background: rgba(255, 255, 255, 0.75);
            color: #475569;
        }
        .step-pill.active {
            background: #1d4ed8;
            color: #ffffff;
            border-color: #1d4ed8;
            box-shadow: 0 4px 14px rgba(29, 78, 216, 0.35);
        }
        .step-pill.done {
            background: rgba(16, 185, 129, 0.14);
            color: #047857;
            border-color: rgba(16, 185, 129, 0.4);
        }

        /* Elevated Suggestion Chip Cards */
        div.stButton > button {
            border-radius: 14px !important;
            font-weight: 600 !important;
            padding: 0.7rem 1rem !important;
            border: 1px solid rgba(37, 99, 235, 0.2) !important;
            background: #ffffff !important;
            color: #0f172a !important;
            box-shadow: 0 2px 10px rgba(15, 23, 42, 0.05) !important;
            transition: all 0.16s ease !important;
        }
        div.stButton > button:hover {
            transform: translateY(-2px) !important;
            border-color: #2563eb !important;
            box-shadow: 0 8px 22px rgba(37, 99, 235, 0.18) !important;
            color: #1d4ed8 !important;
        }

        /* Primary CTA Button */
        div.stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #003580 0%, #2563eb 100%) !important;
            border: none !important;
            color: #ffffff !important;
            box-shadow: 0 6px 20px rgba(37, 99, 235, 0.35) !important;
        }
        div.stButton > button[kind="primary"]:hover {
            box-shadow: 0 10px 26px rgba(37, 99, 235, 0.45) !important;
            color: #ffffff !important;
        }

        /* Chat bubbles */
        [data-testid="stChatMessage"] {
            border-radius: 16px;
            padding: 0.85rem 1.1rem;
            margin-bottom: 0.55rem;
            border: 1px solid rgba(148, 163, 184, 0.2);
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
        }

        /* Dark Mode Overrides */
        @media (prefers-color-scheme: dark) {
            .stApp {
                background: radial-gradient(circle at 50% 10%, #0f172a 0%, #070b14 70%, #03050a 100%);
            }
            .step-pill {
                background: rgba(30, 41, 59, 0.7);
                color: #cbd5e1;
                border-color: rgba(148, 163, 184, 0.25);
            }
            .step-pill.done {
                color: #34d399;
            }
            div.stButton > button {
                background: rgba(30, 41, 59, 0.78) !important;
                color: #f1f5f9 !important;
                border-color: rgba(96, 165, 250, 0.25) !important;
            }
            div.stButton > button:hover {
                background: rgba(37, 99, 235, 0.24) !important;
                color: #ffffff !important;
                border-color: #60a5fa !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
