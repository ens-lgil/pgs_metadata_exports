import sys, os.path
import pandas as pd
from pgs_exports.PGSExport import PGSExport


#---------------------#
# Spreadsheet methods #
#---------------------#

class PGSExportAllMetadata(PGSExport):

    def create_readme_spreadsheet(self, release):
        """ Info/readme spreadsheet """

        readme_data = {}

        readme_data['PGS Catalog version'] = [release]
        readme_data['Number of Polygenic Scores'] = [len(self.data['score'])]
        readme_data['Number of Traits'] = [len(self.data['trait'])]
        readme_data['Number of Publications'] = [len(self.data['publication'])]

        df = pd.DataFrame(readme_data)
        df = df.transpose()
        df.to_excel(self.writer, sheet_name="Readme", header=False)

# #---------------------#
# # Main running method #
# #---------------------#

# def run(*args):
#     if (len(args) == 0):
#         print("ERROR: missing argument providing the path to the export directory")
#         print("Please use the command line with: --script-args <path_to_the_export_directory>")
#         exit()

#     dirpath = args[0] # e.g. '../../../datafiles/export/'
#     datadir = dirpath+"all_metadata/"
#     filename = datadir+'pgs_all_metadata.xlsx'

#     csv_prefix = datadir+'pgs_all'

#     if not os.path.isdir(datadir):
#         try:
#             os.mkdir(datadir)
#         except OSError:
#             print ("Creation of the directory %s failed" % datadir)

#     if not os.path.isdir(datadir):
#         print("Can't create a directory for the metadata ("+datadir+")")
#         exit(1)

#     # Create export object
#     pgs_export = PGSExportAllMetadata(filename)

#     # Info/readme spreadsheet
#     pgs_export.create_readme_spreadsheet()

#     # Build the spreadsheets
#     pgs_export.generate_sheets(csv_prefix)

#     # Close the Pandas Excel writer and output the Excel file.
#     pgs_export.save()

#     # Create a md5 checksum for the spreadsheet
#     pgs_export.create_md5_checksum()

#     # Generate a tar file of the study data
#     pgs_export.generate_tarfile(dirpath+"pgs_all_metadata.tar.gz",datadir)
