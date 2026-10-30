// Publish only the static app to gh-pages; never include practice databases.
const {execFileSync} = require('node:child_process');
function git(args, input) {
  return execFileSync('git', args, {cwd:require('node:path').join(__dirname,'..'), input, encoding:'utf8'}).trim();
}
const files = ['index.html','style.css','app.js','bank.js','favicon.svg'];
try {
  git(['diff','HEAD','--exit-code','--',...files]);
  const entries = files.map(file => {
    const entry = git(['ls-tree','HEAD','--',file]);
    if (!entry || !entry.startsWith('100644 blob ')) throw new Error(`Commit ${file} before deploying.`);
    return entry;
  });
  const empty = git(['hash-object','-w','--stdin'], '');
  entries.push(`100644 blob ${empty}\t.nojekyll`);
  const tree = git(['mktree'], entries.join('\n')+'\n');
  let parent;
  if (git(['ls-remote','--heads','origin','refs/heads/gh-pages'])) {
    git(['fetch','origin','gh-pages']);
    parent = git(['rev-parse','FETCH_HEAD']);
    if (git(['rev-parse',`${parent}^{tree}`]) === tree) {
      console.log('The gh-pages branch already contains the current website.');
      process.exit(0);
    }
  }
  const commit = git(['commit-tree', tree, ...(parent ? ['-p',parent] : []), '-m','Publish Salt Bank browser demo']);
  git(['push','origin',`${commit}:refs/heads/gh-pages`]);
  console.log('Published static files to gh-pages.');
  console.log('One-time setup: repository Settings → Pages → Deploy from a branch → gh-pages / (root) → Save.');
  console.log('Demo address after Pages deploys: https://hosannaute.github.io/salt-bank-atm/');
} catch (error) {
  console.error('Deployment did not complete. Commit app changes and check GitHub push access.');
  console.error(error.message);
  process.exitCode = 1;
}
