import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import Button from './Button';
import Icon from './Icon';

describe('Button Component', () => {
  it('renders with text', () => {
    render(<Button>Click Me</Button>);
    expect(screen.getByText('Click Me')).toBeInTheDocument();
  });

  it('renders with icon only', () => {
    render(
      <Button icon={<Icon name="send" />} aria-label="Send" />
    );
    const button = screen.getByRole('button', { name: 'Send' });
    expect(button).toBeInTheDocument();
    expect(button.querySelector('svg')).toBeInTheDocument();
  });

  it('renders with icon and text', () => {
    render(
      <Button icon={<Icon name="plus" />}>
        New Chat
      </Button>
    );
    expect(screen.getByText('New Chat')).toBeInTheDocument();
    expect(screen.getByRole('button').querySelector('svg')).toBeInTheDocument();
  });

  it('applies primary variant by default', () => {
    render(<Button>Primary</Button>);
    const button = screen.getByRole('button');
    expect(button).toHaveClass('btn-primary');
  });

  it('applies secondary variant', () => {
    render(<Button variant="secondary">Secondary</Button>);
    const button = screen.getByRole('button');
    expect(button).toHaveClass('btn-secondary');
  });

  it('applies icon variant', () => {
    render(
      <Button variant="icon" icon={<Icon name="send" />} aria-label="Send" />
    );
    const button = screen.getByRole('button');
    expect(button).toHaveClass('btn-icon');
  });

  it('applies ghost variant', () => {
    render(<Button variant="ghost">Ghost</Button>);
    const button = screen.getByRole('button');
    expect(button).toHaveClass('btn-ghost');
  });

  it('applies small size', () => {
    render(<Button size="sm">Small</Button>);
    const button = screen.getByRole('button');
    expect(button).toHaveClass('btn-sm');
  });

  it('applies medium size by default', () => {
    render(<Button>Medium</Button>);
    const button = screen.getByRole('button');
    expect(button).toHaveClass('btn-md');
  });

  it('applies large size', () => {
    render(<Button size="lg">Large</Button>);
    const button = screen.getByRole('button');
    expect(button).toHaveClass('btn-lg');
  });

  it('applies icon-only class when only icon is provided', () => {
    render(
      <Button icon={<Icon name="send" />} aria-label="Send" />
    );
    const button = screen.getByRole('button');
    expect(button).toHaveClass('btn-icon-only');
  });

  it('does not apply icon-only class when both icon and text provided', () => {
    render(
      <Button icon={<Icon name="send" />}>Send</Button>
    );
    const button = screen.getByRole('button');
    expect(button).not.toHaveClass('btn-icon-only');
  });

  it('can be disabled', () => {
    render(<Button disabled>Disabled</Button>);
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
  });

  it('applies custom className', () => {
    render(<Button className="custom-class">Custom</Button>);
    const button = screen.getByRole('button');
    expect(button).toHaveClass('custom-class');
    expect(button).toHaveClass('btn'); // Base class still applied
  });

  it('passes through other props', () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick} data-testid="test-btn">Click</Button>);
    const button = screen.getByTestId('test-btn');
    expect(button).toBeInTheDocument();
  });
});
