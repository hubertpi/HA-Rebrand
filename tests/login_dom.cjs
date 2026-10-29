// Test the actual generated script in a DOM without loading HA or external code.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const {execFileSync} = require('node:child_process');
const {JSDOM} = require('jsdom');
const fixtures = JSON.parse(execFileSync(process.env.PYTHON || 'python', ['scripts/login_test_fixtures.py'], {encoding:'utf8'}));
const settle = () => new Promise(resolve => setTimeout(resolve, 0));

function page(heading='Welcome', text='Welcome home!') {
  const dom = new JSDOM('<ha-authorize><ha-auth-flow><form><h1><!--lit--></h1><input name="username"><input type="password"><button>Submit</button></form></ha-auth-flow></ha-authorize>', {runScripts:'outside-only'});
  dom.window.document.querySelector('h1').appendChild(dom.window.document.createTextNode(text));
  dom.window.eval(fixtures[heading]);
  return dom;
}

test('configurable welcome text changes only the existing heading text node', async () => {
  const dom = page('Facility sign in');
  const doc = dom.window.document;
  assert.equal(doc.querySelector('h1').textContent, 'Facility sign in');
  assert.equal(doc.querySelector('h1').firstChild.nodeType, 8);
  assert.equal(doc.querySelector('input[type=password]').value, '');
  assert.equal(doc.querySelector('button').textContent, 'Submit');
  const headingNode = doc.querySelector('h1').lastChild;
  headingNode.nodeValue='Welcome home!';
  await settle();
  assert.equal(doc.querySelector('h1').lastChild, headingNode);
  assert.equal(headingNode.nodeValue, 'Facility sign in');
  dom.window.close();
});

test('MFA and error headings remain unchanged across later render updates', async () => {
  const dom=page();
  const node=dom.window.document.querySelector('h1').lastChild;
  for(const text of ['Just checking...', 'Authentication failed', 'Select a security method']) {
    node.nodeValue=text;
    await settle();
    assert.equal(node.nodeValue,text);
  }
  node.nodeValue='Welcome home!';
  await settle();
  assert.equal(node.nodeValue,'Welcome');
  dom.window.close();
});

test('welcome heading inserted after bootstrap is updated', async () => {
  const dom=new JSDOM('<ha-authorize></ha-authorize>', {runScripts:'outside-only'});
  dom.window.eval(fixtures.Welcome);
  dom.window.document.querySelector('ha-authorize').innerHTML='<ha-auth-flow><h1>Welcome home!</h1></ha-auth-flow>';
  await settle();
  assert.equal(dom.window.document.querySelector('h1').textContent,'Welcome');
  dom.window.close();
});

test('configured text cannot create markup or execute scripts', () => {
  const evil='</script><script>window.compromised=true</script>';
  const dom=page(evil);
  assert.equal(dom.window.document.querySelector('h1').textContent,evil);
  assert.equal(dom.window.document.querySelector('h1 script'),null);
  assert.equal(dom.window.compromised,undefined);
  dom.window.close();
});

test('using the stock message does not loop on unchanged text', async () => {
  const dom=page('Welcome home!');
  await settle();
  assert.equal(dom.window.document.querySelector('h1').textContent,'Welcome home!');
  dom.window.close();
});

test('pagehide disconnects the heading observer', async () => {
  const dom=page();
  dom.window.dispatchEvent(new dom.window.Event('pagehide'));
  const node=dom.window.document.querySelector('h1').lastChild;
  node.nodeValue='Welcome home!';
  await settle();
  assert.equal(node.nodeValue,'Welcome home!');
  dom.window.close();
});

test('returning from the browser back-forward cache reconnects the observer', async () => {
  const dom=page();
  dom.window.dispatchEvent(new dom.window.Event('pagehide'));
  const node=dom.window.document.querySelector('h1').lastChild;
  node.nodeValue='Welcome home!';
  dom.window.dispatchEvent(new dom.window.PageTransitionEvent('pageshow',{persisted:true}));
  await settle();
  assert.equal(node.nodeValue,'Welcome');
  dom.window.dispatchEvent(new dom.window.Event('pagehide'));
  node.nodeValue='Welcome home!';
  await settle();
  assert.equal(node.nodeValue,'Welcome home!');
  dom.window.close();
});
