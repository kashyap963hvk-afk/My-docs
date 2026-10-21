# Use FakeCloud (free AWS on this VM). Run with:  source scripts/use_fakecloud.sh
export AWS_ENDPOINT_URL=http://localhost:4566
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
echo "Target: FakeCloud ($AWS_ENDPOINT_URL)"
