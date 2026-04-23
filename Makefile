.PHONY: install run clean publish test

# Cài package từ thư mục hiện tại (editable mode)
install:
	pip install -e .

# Cài package từ thư mục hiện tại với dev dependencies
install-dev:
	pip install -e ".[all]"

# Build package để publish
build:
	python3 -m build

# Publish lên PyPI (cần có tài khoản PyPI)
publish: build
	twine upload dist/*

# Publish lên Test PyPI (thử nghiệm)
publish-test: build
	twine upload --repository testpypi dist/*

# Cài từ PyPI (sau khi publish)
install-pip:
	pip install vipe-server-dashboard

# Chạy chương trình
run: install
	vipe

# Test
test:
	python3 -m pytest

# Clean
clean:
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ __pycache__/ */__pycache__/ */*/__pycache__/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
