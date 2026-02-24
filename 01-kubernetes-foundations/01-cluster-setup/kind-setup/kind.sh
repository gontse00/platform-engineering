# 1. Identify architecture
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
    URL="https://kind.sigs.k8s.io/dl/v0.31.0/kind-darwin-arm64"
else
    URL="https://kind.sigs.k8s.io/dl/v0.31.0/kind-darwin-amd64"
fi

# 2. Download the binary
echo "Downloading kind v0.31.0 for $ARCH..."
curl -Lo ./kind "$URL"

# 3. Install and Clean up
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind

# 4. Verify
echo "Upgrade complete!"
kind version
