const { spawn } = require('child_process');
const path = require('path');
const electron = require('electron');

console.log('Starting launch verification...');
console.log('Electron binary path:', electron);
const appPath = path.resolve(__dirname, '..');
console.log('App path:', appPath);

let isKilledIntentionally = false;

const child = spawn(electron, [appPath], {
  stdio: 'inherit',
  env: {
    ...process.env,
  }
});

let timer = setTimeout(() => {
  console.log('Electron ran successfully for 5 seconds without crashing.');
  console.log('Terminating Electron...');
  isKilledIntentionally = true;
  child.kill();
  process.exit(0);
}, 5000);

child.on('exit', (code, signal) => {
  clearTimeout(timer);
  if (isKilledIntentionally) {
    console.log('Electron process exited as expected after being killed.');
  } else {
    console.error(`Electron process exited prematurely with code ${code}, signal ${signal}`);
    process.exit(1);
  }
});

child.on('error', (err) => {
  clearTimeout(timer);
  console.error('Failed to spawn Electron process:', err);
  process.exit(1);
});
