from base64 import b64decode


def rp_url_base():
    return [
        b64decode(
            'aHR0cHM6Ly93d3cucmFjaW5ncG9zdC5jb206NDQzL3Byb2ZpbGUvY291cnNlL2ZpbHRlci9yZXN1bHRz'
        ).decode('utf-8'),
        b64decode(
            'aHR0cHM6Ly93d3cucmFjaW5ncG9zdC5jb20vcmVzdWx0cw=='
        ).decode('utf-8')
    ]


def get_all_rp_race_results(track, year):

    xy = rp_url_base()
    code = 'flat'

    if track.rp_track_code is None:
        return

    url = f'{xy[0]}/{track.rp_track_code}/{year}/{code}/all-races'

    print(url)