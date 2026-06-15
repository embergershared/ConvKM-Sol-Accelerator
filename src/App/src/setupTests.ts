// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';

// jsdom does not implement ResizeObserver; Fluent UI components
// (e.g. MessageBar) call it during layout effects in tests.
if (typeof window !== 'undefined' && typeof (window as any).ResizeObserver === 'undefined') {
  (window as any).ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}
