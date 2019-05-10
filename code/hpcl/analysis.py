import Command,os
import numpy as np
#import matplotlib.pyplot as plt
#from matplotlib.ticker import MaxNLocator
#plt.style.use('seaborn')

appnames = {'E3SM': 'E3SM', 'enzo-dev':'Enzo', 'genecode':'GENE', 'lammps':'LAMMPS', 'LATTE':'LATTE', 'namd':'NAMD', 'Nek5000':'NEK5000', 'nwchem':'NWChem', 'qmcpack':'QMCPACK', 'FLASH3and4': 'FLASH'}

category_names = ['Science','Math','Infrastructure','Tests','Documentation','External','Other']
categories = {}
for c in category_names: categories[c] = []
suffixes = {'C/C++' : ['h','H'], 'C': ['c'],  'C++': ['hh', 'hpp', 'hxx', 'H', 'C', 'cxx', 'cc', 'cpp'],
        'Fortran' : ['f', 'f90', 'F', 'F90'], 'Python': ['py'], 'Java':['java'], 'HTML':['html']}
languages = {}
for lang,suffix in suffixes.items(): 
  for s in suffix: languages[s] = lang
all_languages = languages.keys()
uncategorized = []  # To help reduce that set, we output all uncategorized path in a file uncategorized.txt

def resetStats():
  global uncategorized, category_names, categories
  for c in category_names: categories[c] = []
  uncategerized = []

def getLibUsage(libname):
  cmd = 'find tmp -type f -exec grep -i %s {} \; -print | grep -e "^tmp" | grep -v ".git"' % libname.lower()
  r,out,err = Command.Command(cmd).run()
  filelist = [x.strip() for x in out.split()]
  return filelist

def getFiles(topdir):
  filelist = []
  for dirpath, dirnames, files in os.walk(topdir):
    for name in files:
      if dirpath.find('/.git') >= 0: continue
      fpath = os.path.join(dirpath, name)
      suffix = name.split('.')[-1]
      if suffix in all_languages: lang = languages[suffix]
      else: lang = 'Other'
      r,out,err = Command.Command("wc -l %s" % fpath.strip()).run()
      if out: nl = int(out.lstrip().strip().split()[0])
      else: nl = 0
      filelist.append((fpath,nl,lang))
  return filelist

def getCategories(reponame):
  global categories
  print('Loading the categories...')
  for cat in categories.keys():
    fname = os.path.join(os.getcwd(), '../../categories/%s' % reponame, cat+'.txt')
    if os.path.exists(fname):
      categories[cat] = [x.strip() for x in open(fname,'r').readlines()]
    # TODO: use actual regular expressions instead of just substrings
  pass

def getCategory(path):
  global uncategorized
  the_category = 'Other'
  for cat in category_names:
    for pattern in categories[cat]:
      if path.find(pattern) >= 0: 
        the_category = cat
  if the_category == 'Other': uncategorized.append(path)
  return the_category

def getStats(topdir,reponame):
  # stats example {'Science': 25275, 'Tests': 95780, 'Infrastructure': 38633, 'Other': 422972, 'Math': 0} 
  getCategories(reponame)
  filelist = getFiles(topdir)
  stats = {}
  for cat in categories.keys(): stats[cat] = 0
  for f in filelist:
    #print f, getCategory(f[0]) 
    stats[getCategory(f[0])] += f[1]
  return stats
  
def updateStats(topdir,stats,reponame):
  # stats example {'Science': 25275, 'Tests': 95780, 'Infrastructure': 38633, 'Other': 422972, 'Math': 0} 
  getCategories(reponame)
  filelist = getFiles(topdir)
  for c in category_names: 
    if not stats.get(c): stats[c] = 0
  for f in filelist:
    #print 'getStats:',f, getCategory(f[0]), f[1]
    stats[getCategory(f[0])] += f[1]
  return stats

def genPlots(years, vals, title, show=False, filename='stats.pdf'):
  FONT_SIZE = 18
  plt.rc('legend', fontsize=FONT_SIZE-2)
  f,ax = plt.subplots(figsize=(8,4), dpi=100)

  ax.grid()
  ax.set_axisbelow(True)

  legendNames = [x.replace('Documentation','Doc.').replace('Infrastructure','Infrastr.') for x in category_names]
  pal = ["#ff9966", "#d11aff", "#4da6ff", "#009933", "#ffff00", "#663300", "#8c8c8c"]  # color palette
  plt.stackplot(years, vals, labels=legendNames, colors=pal, alpha=0.5, linewidth=1, edgecolor='#444444')
  plt.ylabel('Lines of Code (Thousands)')
  if appnames.get(title): plot_title = appnames[title]
  else: plot_title = title
  plt.title(plot_title)
  ax.xaxis.set_major_locator(MaxNLocator(integer=True))
  for item in ([ax.title, ax.xaxis.label, ax.yaxis.label] +
              ax.get_xticklabels() + ax.get_yticklabels()):
    item.set_fontsize(FONT_SIZE)
  ax.tick_params(axis='x', rotation=45)
  ncol = 1
  if title in ['E3SM','FLASH','Nek5000','qmcpack']: ncol=2
  ax.legend(fancybox=True, framealpha=0.7, loc='upper left', ncol=ncol)
  if show: plt.show()
  f.savefig('%s.pdf' %filename, bbox_inches='tight')
  f.savefig('%s.png' %filename, bbox_inches='tight',dpi=100)
