from fuzzywuzzy import fuzz, process
import pandas as pd

def dishMatch(item, dishNames):
	'''
	'''
	df = pd.DataFrame({'item': item, 'dish': dishNames})

	ratio = lambda x: fuzz.ratio(x['item'], x['dish'])
	df['fuzzRatio'] = df.apply(ratio, axis=1)

	partialRatio = lambda x: fuzz.partial_ratio(x['item'], x['dish'])
	df['fuzzPartial'] = df.apply(partialRatio, axis=1)

	tokenSortRatio = lambda x: fuzz.token_sort_ratio(x['item'], x['dish'])
	df['fuzzSortRatio'] = df.apply(tokenSortRatio, axis=1)

	tokenSetRatio = lambda x: fuzz.token_set_ratio(x['item'], x['dish'])
	df['fuzzSetRatio'] = df.apply(tokenSetRatio, axis=1)

	return df
