# Getting Started with Protegrity Protection APIs

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/Protegrity-Developer-Edition/protegrity-developer-edition/main?filepath=samples/python/sample-app-protect-unprotect/getting-started-protection.ipynb)

## 2-Minute to First API Call

This interactive Jupyter notebook provides the fastest way to make your first Protegrity Protection API call. No local setup required—just click the Binder badge above or click [here](https://mybinder.org/v2/gh/Protegrity-Developer-Edition/protegrity-developer-edition/main?filepath=samples/python/sample-app-protect-unprotect/getting-started-protection.ipynb) to launch a browser-based environment.

## What You'll Learn

- How to authenticate with the Protegrity Developer Edition API
- How to protect sensitive data (names, credit cards, etc.)
- How to unprotect data
- How to perform bulk protection operations

## Requirements

**For Both Options:**
- Valid Protegrity Developer Edition credentials. **Get your API credentials here -** [https://www.protegrity.com/developers/dev-edition-api](https://www.protegrity.com/developers/dev-edition-api)

- Internet connection (for API calls)

**For Local Installation Only (Option 2):**
- Python >= 3.12.11

## Quick Start Options

### Option 1: Run in Browser (Recommended for First-Time Users)

Click the Binder badge above to launch an interactive environment. You'll need:
- Email address (from registration)
- Password (from registration)
- API Key (from registration email)

### Option 2: Run Locally

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r samples/python/requirements.txt
   ```
3. Launch Jupyter:
   ```bash
   jupyter notebook samples/python/sample-app-protect-unprotect/getting-started-protection.ipynb
   ```
4. Follow the notebook instructions

## What's Inside

The notebook includes hands-on examples for:

1. **Basic Protection** - Protect and unprotect a name
2. **Multiple Data Elements** - Work with credit cards, SSNs, emails
3. **Bulk Operations** - Protect multiple values at once
4. **Error Handling** - Understand API responses and error codes

## Security Notes

- Credentials are only stored in your browser session
- Never commit credentials to version control
- All API calls use HTTPS encryption
- No data persistence—tokens are cleared after session ends

## Next Steps

After completing this notebook, explore:

- **Data Discovery Samples** - Automatically find and classify sensitive data
- **Semantic Guardrails** - Add AI safety controls
- **Synthetic Data Generation** - Create realistic test data

## Support

- **Documentation:** [https://developer.docs.protegrity.com/](https://developer.docs.protegrity.com/)
- **Developer Portal:** [https://www.protegrity.com/developers](https://www.protegrity.com/developers)
- **GitHub Discussions:** [https://github.com/orgs/Protegrity-Developer-Edition/discussions](https://github.com/orgs/Protegrity-Developer-Edition/discussions)
- **API Reference:** [Python SDK Documentation](https://docs.protegrity.com/protectors/10.0/docs/ap/ap_python/)

## License

See [LICENSE](../../../LICENSE) file in the root directory.
