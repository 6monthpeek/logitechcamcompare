import { describe, it, expect } from 'vitest';

describe('Initial Environment and Layout Setup', () => {
  it('verifies standard boolean assertion', () => {
    expect(true).toBe(true);
  });

  it('verifies that the jsdom window environment is present', () => {
    expect(typeof window).not.toBe('undefined');
    expect(typeof document).not.toBe('undefined');
  });

  it('can create a mock DOM element', () => {
    const div = document.createElement('div');
    div.id = 'test-node';
    div.textContent = 'Hello Webcam Compare';
    document.body.appendChild(div);
    
    const element = document.getElementById('test-node');
    expect(element).not.toBeNull();
    expect(element.textContent).toBe('Hello Webcam Compare');
    
    document.body.removeChild(div);
  });
});
