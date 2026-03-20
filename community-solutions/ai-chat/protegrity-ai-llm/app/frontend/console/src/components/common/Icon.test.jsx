import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import Icon from './Icon';

describe('Icon Component', () => {
  it('renders plus icon', () => {
    const { container } = render(<Icon name="plus" />);
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
    expect(svg).toHaveAttribute('width', '16');
    expect(svg).toHaveAttribute('height', '16');
  });

  it('renders chevronLeft icon', () => {
    const { container } = render(<Icon name="chevronLeft" />);
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('renders chevronRight icon', () => {
    const { container } = render(<Icon name="chevronRight" />);
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('renders send icon', () => {
    const { container } = render(<Icon name="send" />);
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('renders check icon', () => {
    const { container } = render(<Icon name="check" />);
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('renders message icon', () => {
    const { container } = render(<Icon name="message" />);
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('applies custom size', () => {
    const { container } = render(<Icon name="send" size={24} />);
    const svg = container.querySelector('svg');
    expect(svg).toHaveAttribute('width', '24');
    expect(svg).toHaveAttribute('height', '24');
  });

  it('applies default size of 16', () => {
    const { container } = render(<Icon name="send" />);
    const svg = container.querySelector('svg');
    expect(svg).toHaveAttribute('width', '16');
    expect(svg).toHaveAttribute('height', '16');
  });

  it('applies custom className', () => {
    const { container } = render(<Icon name="send" className="custom-icon" />);
    const svg = container.querySelector('svg');
    expect(svg).toHaveClass('custom-icon');
  });

  it('has correct viewBox', () => {
    const { container } = render(<Icon name="send" />);
    const svg = container.querySelector('svg');
    expect(svg).toHaveAttribute('viewBox', '0 0 24 24');
  });

  it('has correct stroke attributes', () => {
    const { container } = render(<Icon name="send" />);
    const svg = container.querySelector('svg');
    expect(svg).toHaveAttribute('fill', 'none');
    expect(svg).toHaveAttribute('stroke', 'currentColor');
    expect(svg).toHaveAttribute('stroke-width', '2');
  });

  it('returns null for unknown icon', () => {
    const { container } = render(<Icon name="unknown" />);
    expect(container.firstChild).toBeNull();
  });

  it('logs warning for unknown icon', () => {
    const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    render(<Icon name="unknown" />);
    expect(consoleWarnSpy).toHaveBeenCalledWith('Icon "unknown" not found');
    consoleWarnSpy.mockRestore();
  });

  it('passes through additional props', () => {
    const { container } = render(
      <Icon name="send" data-testid="test-icon" aria-label="Send icon" />
    );
    const svg = container.querySelector('svg');
    expect(svg).toHaveAttribute('data-testid', 'test-icon');
    expect(svg).toHaveAttribute('aria-label', 'Send icon');
  });
});
