#!/bin/bash

REPO_URL="https://github.com/Merdeus/dndinventory.git"
BASE_DIR="/opt/dndinventory"
REPO_DIR="$BASE_DIR/dndinventory"
NPM_DIR="$REPO_DIR/react"
PYTHON_DIR="$REPO_DIR/server"

NPM_SCRIPT="build"
PYTHON_SCRIPT="bot.py"
CHECK_INTERVAL=10

LOCK_FILE="/tmp/ampbot.lock"

if [ -f "$LOCK_FILE" ]; then
  echo "Another instance of the script is already running. Exiting."
  exit 1
fi

echo $$ > "$LOCK_FILE"

cleanup() {
  rm -f "$LOCK_FILE"
#  kill $NPM_PID
  kill $PYTHON_PID
  exit
}

trap cleanup EXIT

if [ ! -d "$REPO_DIR" ]; then
  git clone "$REPO_URL"
fi

cd "$REPO_DIR" || exit

run_npm_app() {
  echo "Building npm application..."
  cd "$NPM_DIR" || exit

  npm install
  npm run build

#  serve -s build -l 3000  &
#  NPM_PID=$!
  cd - > /dev/null || exit
}

run_python_server() {
  echo "Running Python server..."
  cd "$PYTHON_DIR" || exit
  source "$PYTHON_DIR/.venv/bin/activate"
  python3 "$PYTHON_SCRIPT"  &
  PYTHON_PID=$!
  deactivate
  cd - > /dev/null || exit
}

update_repo() {
  cd "$REPO_DIR" || exit
  echo "Updating repository..."
  git reset --hard origin/master
  git pull
}

FIRST_RUN=true

while true; do
  git fetch origin

  LOCAL=$(git rev-parse @)
  REMOTE=$(git rev-parse @{u})

  if [ "$LOCAL" != "$REMOTE" ]; then
    echo "New changes detected... updating..."
#    kill $NPM_PID
    kill $PYTHON_PID
    update_repo
    FIRST_RUN=true
  fi

  if [ "$FIRST_RUN" = true ]; then
    #run_npm_app
    run_python_server
    FIRST_RUN=false
  fi 

  sleep $CHECK_INTERVAL
done
