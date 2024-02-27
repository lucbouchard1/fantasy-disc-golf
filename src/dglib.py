import pandas as pd
import drive_data

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

def get_team_data(tournamentData, numWeeks):
    lineups = drive_data.get_lineup_data(['Luc', 'Marina', 'Wyatt'], numWeeks)
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
                if isinstance(row['Start ' + str(p+1)], str):
                    d.append((row.Week, name_to_pdga(row['Start ' + str(p+1)]), 'start'))
                else:
                    d.append(None)

            for p in range(4):
                if isinstance(row['Bench ' + str(p+1)], str):
                    d.append((row.Week, name_to_pdga(row['Bench ' + str(p+1)]), 'bench'))
                else:
                    d.append(None)

            if (not pd.isnull(row['Injury Reserve'])):
                d.append((row.Week, name_to_pdga(row['Injury Reserve']), 'injury'))

        d = pd.DataFrame(d, columns=['week', 'pdga#', 'status'])
        d['coach'] = coach
        data.append(d)

    teamData = pd.concat(data)
    return pd.merge(teamData, tournamentData, on=['week', 'pdga#'])
