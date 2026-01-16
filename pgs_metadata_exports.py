import argparse
import os
import os.path
import shutil
import tarfile
import time

import requests

from pgs_exports.PGSExportGenerator import PGSExportGenerator
from pgs_exports.PGSFtpGenerator import PGSFtpGenerator

large_publication_ids_list = ['PGP000244', 'PGP000263', 'PGP000332', 'PGP000393']


def rest_api_call(url, endpoint, parameters=None):
    """"
    Generic method to perform REST API calls to the PGS Catalog
    > Parameters:
        - url: URL to the REST API
        - endpoint: REST API endpoint
        - parameters: extra parameters to the REST API endpoint, if needed
    > Return type: dictionary
    """
    if not url.endswith('/'):
        url += '/'
    rest_full_url = url + endpoint
    if parameters:
        rest_full_url += '?' + parameters

    print("\t\t> URL: " + rest_full_url)
    try:
        response = requests.get(rest_full_url)
        response_json = response.json()
        # Response with pagination
        if 'next' in response_json:
            count_items = response_json['count']
            results = response_json['results']
            # Loop over the pages
            while response_json['next'] and count_items > len(results):
                time.sleep(1)
                response = requests.get(response_json['next'])
                response_json = response.json()
                results = results + response_json['results']
            if count_items != len(results):
                print(f'The number of items is different than expected: {len(results)} found instead of {count_items}')
        # Response without pagination
        else:
            results = response_json
    except requests.exceptions.RequestException as e:  # This is the correct syntax
        raise SystemExit(e)
    return results


def get_all_pgs_data(url_root):
    """ 
    Fetch all the PGS data via the REST API
    > Parameter:
        - url_root: Root of the REST API URL
    > Return type: dictionary
    """
    data = {}
    for entity in ['score', 'trait', 'publication', 'performance', 'cohort']:
        print(f'\t- Fetch all {entity}s')
        if entity == 'cohort':
            tmp_data = rest_api_call(url_root, f'{entity}/all', 'fetch_all=1')
        else:
            tmp_data = rest_api_call(url_root, f'{entity}/all')
        # Wait a bit to avoid reaching the maximum of allowed queries/min (might be increased)
        time.sleep(5)
        if tmp_data:
            print(f'\t\t> {entity}s: {len(tmp_data)} entries')
            data[entity] = tmp_data
        else:
            print(f'\t/!\\ Error: cannot retrieve "{entity}" data')
    return data


def get_latest_release(url_root) -> dict:
    """
    Fetch the date of the latest the PGS Catalog release
    > Parameter:
        - url_root: Root of the REST API URL
    > Return type: dictionary
    """
    release = ''
    release_data = rest_api_call(url_root, 'release/current')
    if release_data:
        release = release_data
        print(f'\t\t> Release: {release["date"]}')
    else:
        print('\t/!\\ Error: cannot retrieve current release')
    return release


def get_previous_release(url_root):
    """
    Fetch the date of the latest the PGS Catalog release
    > Parameter:
        - url_root: Root of the REST API URL
    > Return type: dictionary
    """
    release = ''
    release_data = rest_api_call(url_root, 'release/all')
    if release_data:
        if 'results' in release_data:
            release = release_data['results'][1]
        else:
            release = release_data[1]
        print(f'\t\t> Previous release: {release["date"]}')
    else:
        print('\t/!\\ Error: cannot retrieve previous release')
    return release


def get_ancestry_categories(url_root):
    """
    Fetch the list of ancestry categories
    > Parameter:
        - url_root: Root of the REST API URL
    > Return type: dictionary
    """
    data = {}
    ancestry_data = rest_api_call(url_root, 'ancestry_categories')
    if ancestry_data:
        for anc in ancestry_data:
            data[anc] = ancestry_data[anc]['display_category']
    else:
        print('\t/!\\ Error: cannot retrieve the list of ancestry categories')
    return data


def create_pgs_directory(path, force_recreate=None):
    """
    Creates directory for a given PGS
    > Parameters:
        - path: path of the directory
        - force_recreate: if it already exists, remove it before creating it again
    """
    # Remove directory before creating it again
    if force_recreate and os.path.isdir(path):
        try:
            shutil.rmtree(path, ignore_errors=True)
        except OSError:
            print(f'Deletion of the existing directory prior to it\'s regeneration failed ({path}).')
            exit()

    # Create directory if it doesn't exist
    if not os.path.isdir(path):
        try:
            os.mkdir(path, 0o755)
        except OSError:
            print(f'Creation of the directory {path} failed')
            exit()


def tardir(path, tar_name):
    """
    Generates a tarball of the new PGS FTP metadata files
    > Parameters:
        - path: path to the directory containing the files we want to compress
        - tar_name: file name of the tar file
    """
    with tarfile.open(tar_name, "w:gz") as tar_handle:
        for root, dirs, files in os.walk(path):
            for file in files:
                tar_handle.add(os.path.join(root, file))


def check_new_data_entry_in_metadata(dirpath_new, data, release_data):
    """
    Check that the metadata directory for the new Scores and Performance Metrics exists
    > Parameters:
        - dirpath_new: path to the directory where the metadata files have be copied
        - data: dictionary containing the metadata
        - release_data: data related to the current release
    """
    scores_dir = dirpath_new + '/scores/'

    # Score(s)
    missing_score_dir = set()
    for score_id in release_data['released_score_ids']:
        if not os.path.isdir(scores_dir + score_id):
            missing_score_dir.add(score_id)
    # Performance Metric(s)
    missing_perf_dir = set()
    new_performances = release_data['released_performance_ids']
    for perf in [x for x in data['performance'] if x['id'] in new_performances]:
        score_id = perf['associated_pgs_id']
        if not os.path.isdir(scores_dir + score_id):
            missing_perf_dir.add(score_id)

    if len(missing_score_dir) != 0 or len(missing_perf_dir) != 0:
        if len(missing_score_dir) != 0:
            print('/!\\ Missing PGS directories for the new entry(ies):\n - ' + '\n - '.join(list(missing_score_dir)))
        if len(missing_perf_dir) != 0:
            print(
                '/!\\ Missing PGS directories for the new associated Performance Metric entry(ies):\n - ' + '\n - '.join(
                    list(missing_perf_dir)))
        exit(1)
    else:
        print("OK - No missing PGS directory for the new  entry(ies)")


# ===============#
#  Main method  #
# ===============#
def main():
    debug = 0
    tmp_export_dir_name = 'export'
    tmp_ftp_dir_name = 'new_ftp_content'

    # Script parameters
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--url", help='The URL root of the REST API, e.g. "http://127.0.0.1:8000/rest/"',
                           required=True)
    argparser.add_argument("--dir", help=f'The path of the root dir of the metadata "<dir>/{tmp_ftp_dir_name}"',
                           required=True)
    argparser.add_argument("--remote_ftp",
                           help='Flag to indicate whether the FTP is remote (FTP protocol) or local (file system) - Default: False (file system)',
                           action='store_true')

    args = argparser.parse_args()

    rest_url_root = args.url
    content_dir = args.dir

    use_remote_ftp = False
    if args.remote_ftp:
        use_remote_ftp = True

    if not os.path.isdir(content_dir):
        print(f'Directory {content_dir} can\'t be found!')
        exit(1)

    # Setup new FTP directory
    new_ftp_dir = content_dir + '/' + tmp_ftp_dir_name
    create_pgs_directory(new_ftp_dir, 1)

    # Setup temporary export directory
    export_dir = content_dir + '/' + tmp_export_dir_name + '/'
    create_pgs_directory(export_dir, 1)

    # Fetch all the metadata (via REST API)
    print('\t- Fetch metadata')
    data = get_all_pgs_data(rest_url_root)

    # Fetch releases data (current and previous)
    print('\t- Fetch release dates')
    current_release = get_latest_release(rest_url_root)
    current_release_date = current_release['date']
    previous_release_date = get_previous_release(rest_url_root)['date']

    # Fetch the list of ancestry categories
    print('\t- Fetch ancestry categories')
    ancestry_categories = get_ancestry_categories(rest_url_root)

    # Setup path to some of the extra export files
    scores_list_file = new_ftp_dir + '/pgs_scores_list.txt'
    archive_file_name = '{}/../pgs_ftp_{}.tar.gz'.format(export_dir, current_release_date)

    # -----------------------#
    # Generate Export files #
    # -----------------------#

    # Get the list of published PGS IDs
    score_ids_list = [x['id'] for x in data['score']]

    exports_generator = PGSExportGenerator(export_dir, data, scores_list_file, score_ids_list,
                                           large_publication_ids_list, current_release_date, ancestry_categories, debug)

    # Generate file listing all the released Scores
    exports_generator.generate_scores_list_file()

    # Generate all PGS metadata export files
    exports_generator.call_generate_all_metadata_exports()

    # Generate all PGS metadata export files
    exports_generator.call_generate_large_studies_metadata_exports()

    # Generate PGS metadata export files for each released studies
    exports_generator.call_generate_studies_metadata_exports()

    # ------------------------#
    # Generate FTP structure #
    # ------------------------#
    ftp_generator = PGSFtpGenerator(export_dir, new_ftp_dir, score_ids_list, large_publication_ids_list,
                                    previous_release_date, use_remote_ftp, debug)

    # Build FTP structure for metadata files
    ftp_generator.build_metadata_ftp()

    # Check that the new entries have a PGS directory
    check_new_data_entry_in_metadata(new_ftp_dir, data, current_release)

    # Build FTP structure for the bulk metadata files
    ftp_generator.build_bulk_metadata_ftp()

    # Build FTP structure for the large study metadata files
    ftp_generator.build_large_study_metadata_ftp()

    # Generates the compressed archive to be copied to the EBI Private FTP
    tardir(new_ftp_dir, archive_file_name)

    # Generate release file (containing the release date)
    release_filename = f'{new_ftp_dir}/release_date.txt'
    try:
        release_file = open(release_filename, 'w')
        release_file.write(current_release_date)
        release_file.close()
    except:
        print(f"Can't create the release file '{release_filename}'.")
        exit()


if __name__ == '__main__':
    main()
