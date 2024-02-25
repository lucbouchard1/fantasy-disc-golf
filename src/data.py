import pandas as pd
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# The ID and range of a sample spreadsheet.
SAMPLE_SPREADSHEET_ID = "1IMPV2U6AUae9Xu4zpdAO2h2Mflaco1RHETVLUQXuRrQ"


def get_lineup_data(coaches, weeks):
  """Shows basic usage of the Sheets API.
  Prints values from a sample spreadsheet.
  """
  creds = None
  data = []
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", SCOPES
      )
      creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      token.write(creds.to_json())

  try:
    service = build("sheets", "v4", credentials=creds)

    for coach in coaches:
      data_range = coach + "!A1:M" + str(weeks+1)
      # Call the Sheets API
      sheet = service.spreadsheets()
      result = (
          sheet.values()
          .get(spreadsheetId=SAMPLE_SPREADSHEET_ID, range=data_range)
          .execute()
      )
      values = result.get("values", [])

      if not values:
        print("No data found.")
        return

      data += [values[i] for i in range(1, weeks+1)]
  except HttpError as err:
    print(err)

  return pd.DataFrame(data, columns=['Event', 'Week', 'Start 1', 'Start 2', 'Start 3', 'Start 4', 'Start 5',
                              'Start 6', 'Bench 1', 'Bench 2', 'Bench 3', 'Bench 4', 'Injury Reserve'])


if __name__ == "__main__":
  print(get_lineup_data(["Luc", "Marina", "Wyatt"], 1).head())