from bs4 import BeautifulSoup
import requests
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


def download_tournament_data(url, csv_file):
  r = requests.get(url)
  content = r.text

  soup = BeautifulSoup(content, 'html.parser')
  table = soup.find(id="tournament-stats-0")

  result = []
  for row in table.tbody.contents:
      if (row.name != "tr"):
          continue

      result_row = []
      for col in row.contents:
          if (col.name != "td" or 'round-rating' in col['class'] or len(col.contents) == 0):
              continue

          data = col.contents[0]
          if (data.name is None):
              result_row.append(str(data))
          elif (data.name == 'a'):
              result_row.append(str(data.contents[0]))

      result.append(result_row)

  df = pd.DataFrame(result)
  df.to_csv(csv_file, header=False, index=False)

def get_lineup_data(coaches, weeks):
  """Shows basic usage of the Sheets API.
  Prints values from a sample spreadsheet.
  """
  creds = None
  data_frames = {}
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

      rows = []
      for i in range(1, weeks+1):
        rows.append(values[i] + ([] if len(values[i]) == len(values[0]) else [None]))

      df = pd.DataFrame(rows, columns=values[0])

      # Clean data
      df['Week'] = df['Week'].astype(int)
      for row in values[0][2:]:
        df[row] = df[row].str.lower()
        df[row] = df[row].str.strip()

      data_frames[coach] = df
  except HttpError as err:
    print(err)

  return data_frames

def get_points(place):
    if place == 1:
        return 8
    elif place < 6:
        return 3
    elif place < 11:
        return 1
    return 0

def get_pdga_num_map():
    pdgaDb = pd.read_csv('data/pdga_db.csv')
    return {row['name']: row['pdga#'] for _, row in pdgaDb.iterrows()}

def get_tournaments(year=2024):
    return pd.read_csv('data/' + str(year) + '/tournaments.csv')

def get_tournament_data(year=2024):
    folder = 'data/' + str(year) + '/'
    tournaments = get_tournaments()

    data = []
    for _, t in tournaments.iterrows():
        d = pd.read_csv(folder + t.file, header=None)
        d = pd.concat([d.iloc[:,0:5], d.iloc[:,-2:]], axis=1)
        d.columns=['place', 'name', 'pdga#', 'rating', 'par', 'total', 'prize']
        d['type'] = t.type
        d['week'] = t.week
        d['tournament'] = t.tournament_name
        data.append(d)

    data = pd.concat(data)

    data['rawPoints'] = data['place'].apply(get_points)
    data['fantasyPoints'] = data['rawPoints'] * (1 + (data['type'] == 'm'))
    data['cash'] = data['prize'].str[1:].str.replace(',', '').astype(float).fillna(0)
    return data

def get_team_data(tournamentData, numWeeks, include_nonplaying=False):
    lineups = get_lineup_data(['Luc', 'Marina', 'Wyatt'], numWeeks)
    pdgaMap = get_pdga_num_map()

    def name_to_pdga(name):
        name = name.lower()
        name = name.strip()
        if name not in pdgaMap:
            print("Error:", name, "not found in PDGA number database")
            return None
        return pdgaMap[name]

    data = []
    for coach in lineups:
        raw = lineups[coach]
        d = []

        for w in range(numWeeks):
            row = raw.iloc[w]
            for p in range(6):
                curr = row['Start ' + str(p+1)]
                if isinstance(curr, str):
                    d.append((row.Week, curr, name_to_pdga(curr), 'start'))
                else:
                    d.append(None)

            for p in range(4):
                curr = row['Bench ' + str(p+1)]
                if isinstance(curr, str):
                    d.append((row.Week, curr, name_to_pdga(curr), 'bench'))
                else:
                    d.append(None)

            if (not pd.isnull(row['Injury Reserve'])):
                d.append((row.Week, row['Injury Reserve'], name_to_pdga(row['Injury Reserve']), 'injury'))

        d = pd.DataFrame(d, columns=['week', 'entered_name', 'pdga#', 'status'])
        d['coach'] = coach
        data.append(d)

    teamData = pd.concat(data)
    result = pd.merge(teamData, tournamentData, on=['week', 'pdga#'], how=('left' if include_nonplaying else 'inner'))
    result['cash'].fillna(0, inplace=True)
    return result

if __name__ == "__main__":
  print("Downloading all tournament data...")
  tournaments = get_tournaments()

  for _, t in tournaments.iterrows():
    download_tournament_data(t['url'], 'data/2024/' + t['file'])
