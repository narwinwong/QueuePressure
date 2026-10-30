"""Plot saved E18 aggregates only; never read raw quotes or evaluate a rule."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent


def main():
    out=ROOT/'regenerated'
    out.mkdir(exist_ok=True)
    result=json.loads((ROOT/'results.json').read_text())
    names=list(result['scenarios'])
    means=[]
    counts=[]
    for name in names:
        item=result['scenarios'][name]['pressure']
        counts.append(item['trades'])
        means.append(item['net_units']/10000/item['trades'] if item['trades'] else float('nan'))
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    axes[0].bar(range(len(names)),means,color=['#245b80' if v>0 else '#a84a3d' for v in means])
    axes[0].set_xticks(range(len(names)),[n.replace('_',' ')+'\nn='+str(c) for n,c in zip(names,counts)])
    axes[0].tick_params(axis='x',labelsize=8)
    axes[0].set_ylabel('Mean conditional round-trip margin (USD per share)')
    axes[0].set_title('Fixed cost and delay scenarios')
    blocks=result['scenarios']['primary']['pressure']['blocks']
    axes[1].bar(range(4),[b['net_units']/10000 for b in blocks],color='#a84a3d')
    axes[1].set_xticks(range(4),['09:35–10:30','10:30–11:30','11:30–12:30','12:30–13:30'],rotation=15)
    axes[1].set_ylabel('Sum of conditional primary margins (USD)')
    axes[1].set_title('Prespecified blocks, source clock')
    for ax in axes:
        ax.axhline(0,color='black',linewidth=.8)
        ax.spines[['top','right']].set_visible(False)
    fig.suptitle('AAPL, June 21, 2012: fixed queue-pressure reference screen')
    fig.text(.5,.025,'One stock, one day. Hypothetical quote touches and assumed costs; no account return, confidence interval or OOS claim.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.08,1,.94))
    fig.savefig(out/'conditional_margins.png',dpi=160)
    plt.close(fig)


if __name__=='__main__': main()
