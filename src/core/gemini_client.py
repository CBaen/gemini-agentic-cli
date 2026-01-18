"""
Gemini Client - Direct Python SDK Integration

Uses Google Generative AI Python SDK with OAuth credentials.
Bypasses the gemini CLI which has subprocess issues on Windows.
"""

import json
import os
from pathlib import Path
from typing import Optional
import google.generativeai as genai
from google.auth.credentials import Credentials
from google.oauth2.credentials import Credentials as OAuth2Credentials


class GeminiClient:
    """
    Direct Gemini API client using Python SDK with OAuth credentials.

    Supports multi-account rotation by reading from ~/.gemini/oauth_creds_accountN.json files.
    """

    def __init__(self, gemini_dir: Optional[Path] = None):
        """
        Initialize Gemini client.

        Args:
            gemini_dir: Path to .gemini directory (default: ~/.gemini)
        """
        self.gemini_dir = gemini_dir or Path.home() / ".gemini"
        self._current_account = None
        self._client = None

    def _load_credentials(self, account: int) -> OAuth2Credentials:
        """
        Load OAuth credentials for specified account.

        Args:
            account: Account number (1 or 2)

        Returns:
            OAuth2Credentials object
        """
        creds_file = self.gemini_dir / f"oauth_creds_account{account}.json"

        if not creds_file.exists():
            raise FileNotFoundError(
                f"Credentials file not found: {creds_file}\n"
                f"Please authenticate account {account} first."
            )

        with open(creds_file, 'r') as f:
            creds_data = json.load(f)

        # Create OAuth2Credentials object from JSON
        credentials = OAuth2Credentials(
            token=creds_data.get('access_token'),
            refresh_token=creds_data.get('refresh_token'),
            token_uri="https://oauth2.googleapis.com/token",
            client_id="681255809395-oo8ft2oprdrnp9e3aqf6av3hmdib135j.apps.googleusercontent.com",
            scopes=creds_data.get('scope', '').split()
        )

        return credentials

    def switch_account(self, account: int):
        """
        Switch to specified account.

        Args:
            account: Account number (1 or 2)
        """
        if account not in [1, 2]:
            raise ValueError(f"Invalid account: {account}. Must be 1 or 2.")

        credentials = self._load_credentials(account)

        # Configure genai with credentials
        genai.configure(credentials=credentials)
        self._current_account = account

    def query(
        self,
        prompt: str,
        model: str = "gemini-2.5-flash-lite",
        account: Optional[int] = None
    ) -> str:
        """
        Send query to Gemini and return response.

        Args:
            prompt: User prompt
            model: Model ID (default: gemini-2.5-flash-lite)
            account: Account number (1 or 2), or None to use current

        Returns:
            Gemini's response text
        """
        # Switch account if specified
        if account is not None and account != self._current_account:
            self.switch_account(account)
        elif self._current_account is None:
            # No account set, default to account 1
            self.switch_account(1)

        try:
            # Create model instance
            model_instance = genai.GenerativeModel(model)

            # Generate response
            response = model_instance.generate_content(prompt)

            return response.text

        except Exception as e:
            raise RuntimeError(f"Gemini API error: {e}")


def query_gemini(
    prompt: str,
    account: int = 1,
    model: str = "gemini-2.5-flash-lite"
) -> str:
    """
    Convenience function to query Gemini.

    Args:
        prompt: User prompt
        account: Account number (1 or 2)
        model: Model ID

    Returns:
        Gemini's response text
    """
    client = GeminiClient()
    return client.query(prompt, model=model, account=account)
