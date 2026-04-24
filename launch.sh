#!/bin/bash
# ============================================================
# The Passive Approach to Generating Wealth
# Launch Script
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "============================================"
echo "  The Passive Approach to Generating Wealth"
echo "============================================"
echo ""

# Get local IP for phone access
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || echo "localhost")

echo "Choose an app to launch:"
echo ""
echo "  1) 💰 Dividend Dashboard"
echo "  2) 📸 Stock Media Manager"
echo "  3) 🚀 Launch Both"
echo ""
read -p "Enter choice (1/2/3): " choice

case $choice in
    1)
        echo ""
        echo "Starting Dividend Dashboard..."
        echo "  Local:   http://localhost:8501"
        echo "  Phone:   http://$LOCAL_IP:8501"
        echo ""
        cd "$SCRIPT_DIR/dividend-dashboard"
        streamlit run app.py --server.address 0.0.0.0 --server.port 8501
        ;;
    2)
        echo ""
        echo "Starting Stock Media Manager..."
        echo "  Local:   http://localhost:8502"
        echo "  Phone:   http://$LOCAL_IP:8502"
        echo ""
        cd "$SCRIPT_DIR/stock-media-manager"
        streamlit run app.py --server.address 0.0.0.0 --server.port 8502
        ;;
    3)
        echo ""
        echo "Starting both apps..."
        echo ""
        echo "  Dividend Dashboard:"
        echo "    Local:   http://localhost:8501"
        echo "    Phone:   http://$LOCAL_IP:8501"
        echo ""
        echo "  Stock Media Manager:"
        echo "    Local:   http://localhost:8502"
        echo "    Phone:   http://$LOCAL_IP:8502"
        echo ""
        cd "$SCRIPT_DIR/dividend-dashboard"
        streamlit run app.py --server.address 0.0.0.0 --server.port 8501 &
        cd "$SCRIPT_DIR/stock-media-manager"
        streamlit run app.py --server.address 0.0.0.0 --server.port 8502
        ;;
    *)
        echo "Invalid choice. Please run again and choose 1, 2, or 3."
        ;;
esac
