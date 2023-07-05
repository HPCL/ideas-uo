import pandas as pd
#from populator.data_etl.db_extractor import DBExtractor
from fuzzywuzzy import process


class AuthorMergerTool:
    @staticmethod
    def get_unique_authors_and_emails(repo, list_of_authors):
        # Merge the author names by fuzzy matching
        unique_authors = AuthorMergerTool._get_unique_authors(list_of_authors)

        # Convert the pandas df to lists
        authors = unique_authors['author'].to_list()
        unique_authors = unique_authors['unique_author'].to_list()

        # Get associated emails
        #db = DBExtractor.instance()
        emails_dfs = [] #[db.get_author_emails(repo, author) for author in authors]

        # Merge based on common email or name

        unique_entries_names = list()
        unique_entries_emails = list()

        for name, unique_name, email_df in zip (authors, unique_authors, emails_dfs):
            
            names_as_set = {name, unique_name}
            emails_as_set = set(email_df['email'].to_list())

            already_in_unique_entries = False
            for index, (unique_names, unique_emails) in enumerate(zip(unique_entries_names, unique_entries_emails)):
                if len(names_as_set.intersection(unique_names)) > 0 or len(emails_as_set.intersection(unique_emails)) > 0:
                    already_in_unique_entries = True
                    unique_entries_names[index].update(names_as_set)
                    unique_entries_emails[index].update(emails_as_set)

            if not already_in_unique_entries:
                unique_entries_names.append(names_as_set)
                unique_entries_emails.append(emails_as_set)  

        # Return the results as a list of tuples of the form:
        #  [(["Sam", "Samuel"], ["sam@cs.uoregon.edu", "samds@uoregon.edu"]),
        #   (["Steve", "Stephen"], ["fickas@cs.uoregon.edu"])]
        results = [(list(names), list(emails)) for names, emails in zip(unique_entries_names, unique_entries_emails)]
        return results

    @staticmethod
    def _get_unique_authors(list_of_authors):
        # print("INFO: Analyzing author names, this can take a few minutes...")
        list_of_authors = sorted(set([author.strip() for author in list_of_authors]))
        results = dict()
        for name in list_of_authors:
            ratio = process.extract(str(name), list_of_authors, limit=10)
            results[name] = ratio
        threshold = 60
        real_names = {}
        count = 0
        done = []

        # Sort by the length of the keys
        items = [(key, val) for _, key, val, in sorted([(len(key1), key1, val1) for key1, val1 in results.items()], reverse=True)]

        for nm, val in items:
            for name, score in val:
                if score < threshold:
                    break
                if name not in done:
                    real_names[count] = [name, nm]
                    done.append(name)
                count += 1
        # Apply manual fixes (when available)

        authors_data = pd.DataFrame.from_dict(real_names, orient='index', columns=['author', 'unique_author'])

        return authors_data
