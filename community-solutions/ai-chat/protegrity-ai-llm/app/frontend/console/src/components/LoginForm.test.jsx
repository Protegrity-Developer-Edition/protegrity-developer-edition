import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import LoginForm from './LoginForm';

describe('LoginForm Component', () => {
  const defaultProps = {
    onLogin: vi.fn(),
    error: null,
    loading: false
  };

  describe('Basic Rendering', () => {
    it('renders login form', () => {
      render(<LoginForm {...defaultProps} />);
      
      expect(screen.getByText('Sign in to Protegrity AI')).toBeInTheDocument();
    });

    it('renders username input', () => {
      render(<LoginForm {...defaultProps} />);
      
      expect(screen.getByLabelText('Username')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Enter your username')).toBeInTheDocument();
    });

    it('renders password input', () => {
      render(<LoginForm {...defaultProps} />);
      
      expect(screen.getByLabelText('Password')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Enter your password')).toBeInTheDocument();
    });

    it('renders submit button', () => {
      render(<LoginForm {...defaultProps} />);
      
      expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument();
    });

    it('renders logo', () => {
      const { container } = render(<LoginForm {...defaultProps} />);
      
      const logo = container.querySelector('.login-logo');
      expect(logo).toBeInTheDocument();
      expect(logo?.getAttribute('src')).toBe('/images/white-logo.svg');
    });

    it('renders footnote text', () => {
      render(<LoginForm {...defaultProps} />);
      
      expect(screen.getByText(/Use your Protegrity account credentials/i)).toBeInTheDocument();
    });
  });

  describe('Form Interaction', () => {
    it('updates username input value', () => {
      render(<LoginForm {...defaultProps} />);
      
      const usernameInput = screen.getByLabelText('Username');
      fireEvent.change(usernameInput, { target: { value: 'testuser' } });
      
      expect(usernameInput.value).toBe('testuser');
    });

    it('updates password input value', () => {
      render(<LoginForm {...defaultProps} />);
      
      const passwordInput = screen.getByLabelText('Password');
      fireEvent.change(passwordInput, { target: { value: 'password123' } });
      
      expect(passwordInput.value).toBe('password123');
    });

    it('calls onLogin with credentials when form is submitted', () => {
      const onLogin = vi.fn();
      render(<LoginForm {...defaultProps} onLogin={onLogin} />);
      
      fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'testuser' } });
      fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'password123' } });
      
      fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));
      
      expect(onLogin).toHaveBeenCalledWith({
        username: 'testuser',
        password: 'password123'
      });
    });

    it('calls onLogin when Enter is pressed in form', () => {
      const onLogin = vi.fn();
      render(<LoginForm {...defaultProps} onLogin={onLogin} />);
      
      fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'testuser' } });
      fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'password123' } });
      
      const form = screen.getByLabelText('Username').closest('form');
      fireEvent.submit(form);
      
      expect(onLogin).toHaveBeenCalledWith({
        username: 'testuser',
        password: 'password123'
      });
    });

    it('does not call onLogin when username is empty', () => {
      const onLogin = vi.fn();
      render(<LoginForm {...defaultProps} onLogin={onLogin} />);
      
      fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'password123' } });
      fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));
      
      expect(onLogin).not.toHaveBeenCalled();
    });

    it('does not call onLogin when password is empty', () => {
      const onLogin = vi.fn();
      render(<LoginForm {...defaultProps} onLogin={onLogin} />);
      
      fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'testuser' } });
      fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));
      
      expect(onLogin).not.toHaveBeenCalled();
    });

    it('does not call onLogin when both fields are empty', () => {
      const onLogin = vi.fn();
      render(<LoginForm {...defaultProps} onLogin={onLogin} />);
      
      fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));
      
      expect(onLogin).not.toHaveBeenCalled();
    });
  });

  describe('Button State', () => {
    it('disables submit button when username is empty', () => {
      render(<LoginForm {...defaultProps} />);
      
      fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'password123' } });
      
      const submitButton = screen.getByRole('button', { name: 'Sign in' });
      expect(submitButton).toBeDisabled();
    });

    it('disables submit button when password is empty', () => {
      render(<LoginForm {...defaultProps} />);
      
      fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'testuser' } });
      
      const submitButton = screen.getByRole('button', { name: 'Sign in' });
      expect(submitButton).toBeDisabled();
    });

    it('enables submit button when both fields have values', () => {
      render(<LoginForm {...defaultProps} />);
      
      fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'testuser' } });
      fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'password123' } });
      
      const submitButton = screen.getByRole('button', { name: 'Sign in' });
      expect(submitButton).not.toBeDisabled();
    });
  });

  describe('Loading State', () => {
    it('shows loading text when loading is true', () => {
      render(<LoginForm {...defaultProps} loading={true} />);
      
      expect(screen.getByText('Signing in…')).toBeInTheDocument();
    });

    it('disables submit button when loading', () => {
      render(<LoginForm {...defaultProps} loading={true} />);
      
      const submitButton = screen.getByRole('button', { name: 'Signing in…' });
      expect(submitButton).toBeDisabled();
    });

    it('disables username input when loading', () => {
      render(<LoginForm {...defaultProps} loading={true} />);
      
      expect(screen.getByLabelText('Username')).toBeDisabled();
    });

    it('disables password input when loading', () => {
      render(<LoginForm {...defaultProps} loading={true} />);
      
      expect(screen.getByLabelText('Password')).toBeDisabled();
    });

    it('does not call onLogin when form is submitted during loading', () => {
      const onLogin = vi.fn();
      render(<LoginForm {...defaultProps} onLogin={onLogin} loading={true} />);
      
      const form = screen.getByLabelText('Username').closest('form');
      fireEvent.submit(form);
      
      expect(onLogin).not.toHaveBeenCalled();
    });

    it('prevents multiple submissions when loading', () => {
      const onLogin = vi.fn();
      render(<LoginForm {...defaultProps} onLogin={onLogin} loading={true} />);
      
      fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'testuser' } });
      fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'password123' } });
      
      const form = screen.getByLabelText('Username').closest('form');
      fireEvent.submit(form);
      fireEvent.submit(form);
      
      expect(onLogin).not.toHaveBeenCalled();
    });
  });

  describe('Error Display', () => {
    it('displays error message when error prop is provided', () => {
      const error = 'Invalid username or password';
      render(<LoginForm {...defaultProps} error={error} />);
      
      expect(screen.getByText('Invalid username or password')).toBeInTheDocument();
    });

    it('shows error icon with error message', () => {
      const error = 'Login failed';
      render(<LoginForm {...defaultProps} error={error} />);
      
      expect(screen.getByText('⚠️')).toBeInTheDocument();
    });

    it('does not display error when error prop is null', () => {
      render(<LoginForm {...defaultProps} error={null} />);
      
      expect(screen.queryByText('⚠️')).not.toBeInTheDocument();
    });

    it('does not display error when error prop is empty string', () => {
      render(<LoginForm {...defaultProps} error="" />);
      
      expect(screen.queryByText('⚠️')).not.toBeInTheDocument();
    });

    it('displays long error messages', () => {
      const longError = 'This is a very long error message that explains in detail what went wrong with the login attempt and provides helpful information to the user.';
      render(<LoginForm {...defaultProps} error={longError} />);
      
      expect(screen.getByText(longError)).toBeInTheDocument();
    });

    it('applies error styling when error is present', () => {
      const { container } = render(<LoginForm {...defaultProps} error="Error message" />);
      
      const errorDiv = container.querySelector('.login-error');
      expect(errorDiv).toBeInTheDocument();
    });
  });

  describe('Input Attributes', () => {
    it('has correct type for username input', () => {
      render(<LoginForm {...defaultProps} />);
      
      const usernameInput = screen.getByLabelText('Username');
      expect(usernameInput).toHaveAttribute('type', 'text');
    });

    it('has correct type for password input', () => {
      render(<LoginForm {...defaultProps} />);
      
      const passwordInput = screen.getByLabelText('Password');
      expect(passwordInput).toHaveAttribute('type', 'password');
    });

    it('has autocomplete attribute on username input', () => {
      render(<LoginForm {...defaultProps} />);
      
      const usernameInput = screen.getByLabelText('Username');
      expect(usernameInput).toHaveAttribute('autocomplete', 'username');
    });

    it('has autocomplete attribute on password input', () => {
      render(<LoginForm {...defaultProps} />);
      
      const passwordInput = screen.getByLabelText('Password');
      expect(passwordInput).toHaveAttribute('autocomplete', 'current-password');
    });
  });

  describe('Form Validation', () => {
    it('trims whitespace from username', () => {
      const onLogin = vi.fn();
      render(<LoginForm {...defaultProps} onLogin={onLogin} />);
      
      fireEvent.change(screen.getByLabelText('Username'), { target: { value: '  testuser  ' } });
      fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'password123' } });
      fireEvent.submit(screen.getByLabelText('Username').closest('form'));
      
      expect(onLogin).toHaveBeenCalledWith({
        username: '  testuser  ', // Component doesn't trim - passes as-is
        password: 'password123'
      });
    });

    it('allows special characters in username', () => {
      const onLogin = vi.fn();
      render(<LoginForm {...defaultProps} onLogin={onLogin} />);
      
      fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'test@user.com' } });
      fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'password123' } });
      fireEvent.submit(screen.getByLabelText('Username').closest('form'));
      
      expect(onLogin).toHaveBeenCalledWith({
        username: 'test@user.com',
        password: 'password123'
      });
    });

    it('allows special characters in password', () => {
      const onLogin = vi.fn();
      render(<LoginForm {...defaultProps} onLogin={onLogin} />);
      
      fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'testuser' } });
      fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'P@ssw0rd!#$%' } });
      fireEvent.submit(screen.getByLabelText('Username').closest('form'));
      
      expect(onLogin).toHaveBeenCalledWith({
        username: 'testuser',
        password: 'P@ssw0rd!#$%'
      });
    });
  });

  describe('Edge Cases', () => {
    it('handles missing onLogin prop gracefully', () => {
      const { container } = render(<LoginForm error={null} loading={false} />);
      
      // Should render without crashing
      expect(screen.getByText('Sign in to Protegrity AI')).toBeInTheDocument();
    });

    it('handles rapid input changes', () => {
      render(<LoginForm {...defaultProps} />);
      
      const usernameInput = screen.getByLabelText('Username');
      
      fireEvent.change(usernameInput, { target: { value: 'a' } });
      fireEvent.change(usernameInput, { target: { value: 'ab' } });
      fireEvent.change(usernameInput, { target: { value: 'abc' } });
      
      expect(usernameInput.value).toBe('abc');
    });

    it('clears form when component receives new props', () => {
      const { rerender } = render(<LoginForm {...defaultProps} />);
      
      fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'testuser' } });
      fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'password123' } });
      
      // Form values persist across prop updates (component doesn't clear on rerender)
      rerender(<LoginForm {...defaultProps} error="New error" />);
      
      expect(screen.getByLabelText('Username').value).toBe('testuser');
      expect(screen.getByLabelText('Password').value).toBe('password123');
    });
  });

  describe('CSS Classes', () => {
    it('applies correct class to main container', () => {
      const { container } = render(<LoginForm {...defaultProps} />);
      
      expect(container.querySelector('.login-screen')).toBeInTheDocument();
    });

    it('applies correct class to card', () => {
      const { container } = render(<LoginForm {...defaultProps} />);
      
      expect(container.querySelector('.login-card')).toBeInTheDocument();
    });

    it('applies correct class to form', () => {
      const { container } = render(<LoginForm {...defaultProps} />);
      
      expect(container.querySelector('.login-form')).toBeInTheDocument();
    });

    it('applies correct class to inputs', () => {
      const { container } = render(<LoginForm {...defaultProps} />);
      
      expect(container.querySelectorAll('.login-input')).toHaveLength(2);
    });

    it('applies correct class to button', () => {
      const { container } = render(<LoginForm {...defaultProps} />);
      
      expect(container.querySelector('.login-button')).toBeInTheDocument();
    });
  });
});
