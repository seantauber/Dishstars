from fuzzywuzzy import fuzz, process
import pandas as pd

def dishMatch(item, dishNames):
	'''
	'''
	df = pd.DataFrame({'item': item, 'dish': dishNames})

	ratio = lamba x: fuzz.ratio(x['item'], x['dish'])
	df['fuzzRatio'] = df.apply(ratio, axis=1)

	return df
	