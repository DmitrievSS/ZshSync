#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Create symlink in ~/.local/bin
mkdir -p ~/.local/bin
ln -sf "$SCRIPT_DIR/zsh_sync" ~/.local/bin/zsh_sync

# Add ~/.local/bin to PATH if not already present
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
    echo "Added ~/.local/bin to PATH in ~/.zshrc"
fi

# Make zsh_sync executable
chmod +x "$SCRIPT_DIR/zsh_sync"

echo "Installation complete! You can now use 'zsh_sync' from any directory."
echo "Please restart your shell or run 'source ~/.zshrc' to update your PATH." 