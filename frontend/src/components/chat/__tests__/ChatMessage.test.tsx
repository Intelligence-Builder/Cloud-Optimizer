import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ChatMessage } from '../ChatMessage';

describe('ChatMessage', () => {
  const mockTimestamp = new Date('2024-01-01T12:00:00Z');

  describe('User Messages', () => {
    it('renders user message correctly', () => {
      render(
        <ChatMessage
          role="user"
          content="Hello, how can I optimize my cloud costs?"
          timestamp={mockTimestamp}
        />
      );

      expect(screen.getByText('Hello, how can I optimize my cloud costs?')).toBeInTheDocument();
      expect(screen.getByText('U')).toBeInTheDocument();
    });

    it('applies correct styling for user messages', () => {
      const { container } = render(
        <ChatMessage
          role="user"
          content="Test message"
          timestamp={mockTimestamp}
        />
      );

      const messageContainer = container.querySelector('.chat-message-user');
      expect(messageContainer).toBeInTheDocument();
    });

    it('renders user message as plain text (not markdown)', () => {
      render(
        <ChatMessage
          role="user"
          content="**Bold text** and _italic text_"
          timestamp={mockTimestamp}
        />
      );

      // Should render markdown syntax literally for user messages
      expect(screen.getByText(/\*\*Bold text\*\*/)).toBeInTheDocument();
    });

    it('displays timestamp correctly', () => {
      render(
        <ChatMessage
          role="user"
          content="Test"
          timestamp={mockTimestamp}
        />
      );

      // date-fns formatDistanceToNow should render something
      const timestamp = screen.getByText(/ago$/);
      expect(timestamp).toBeInTheDocument();
    });
  });

  describe('Assistant Messages', () => {
    it('renders assistant message correctly', () => {
      render(
        <ChatMessage
          role="assistant"
          content="I can help you optimize your cloud costs."
          timestamp={mockTimestamp}
        />
      );

      expect(screen.getByText('I can help you optimize your cloud costs.')).toBeInTheDocument();
      expect(screen.getByText('AI')).toBeInTheDocument();
    });

    it('applies correct styling for assistant messages', () => {
      const { container } = render(
        <ChatMessage
          role="assistant"
          content="Test message"
          timestamp={mockTimestamp}
        />
      );

      const messageContainer = container.querySelector('.chat-message-assistant');
      expect(messageContainer).toBeInTheDocument();
    });

    it('renders markdown content for assistant messages', () => {
      render(
        <ChatMessage
          role="assistant"
          content="# Heading\n\nThis is **bold** text."
          timestamp={mockTimestamp}
        />
      );

      // ReactMarkdown should render the heading
      const heading = screen.getByRole('heading', { level: 1 });
      expect(heading).toHaveTextContent('Heading');

      // Bold text should be rendered (but testing exact element is tricky with markdown)
      expect(screen.getByText(/bold/)).toBeInTheDocument();
    });

    it('renders code blocks with syntax highlighting', () => {
      const codeContent = '```python\ndef hello():\n    print("Hello")\n```';

      const { container } = render(
        <ChatMessage
          role="assistant"
          content={codeContent}
          timestamp={mockTimestamp}
        />
      );

      // Check for code element with hljs class
      const codeElement = container.querySelector('.hljs');
      expect(codeElement).toBeInTheDocument();
      expect(codeElement?.textContent).toContain('def');
    });

    it('shows streaming indicator when isStreaming is true', () => {
      const { container } = render(
        <ChatMessage
          role="assistant"
          content="Typing..."
          timestamp={mockTimestamp}
          isStreaming={true}
        />
      );

      // Check for the animated pulse indicator
      const pulseIndicator = container.querySelector('.animate-pulse');
      expect(pulseIndicator).toBeInTheDocument();
    });

    it('does not show streaming indicator when isStreaming is false', () => {
      const { container } = render(
        <ChatMessage
          role="assistant"
          content="Complete message"
          timestamp={mockTimestamp}
          isStreaming={false}
        />
      );

      const pulseIndicator = container.querySelector('.animate-pulse');
      expect(pulseIndicator).not.toBeInTheDocument();
    });

    it('defaults to not streaming when isStreaming is undefined', () => {
      const { container } = render(
        <ChatMessage
          role="assistant"
          content="Complete message"
          timestamp={mockTimestamp}
        />
      );

      const pulseIndicator = container.querySelector('.animate-pulse');
      expect(pulseIndicator).not.toBeInTheDocument();
    });
  });

  describe('Message Layout', () => {
    it('aligns user messages to the right', () => {
      const { container } = render(
        <ChatMessage
          role="user"
          content="Test"
          timestamp={mockTimestamp}
        />
      );

      const messageWrapper = container.querySelector('.justify-end');
      expect(messageWrapper).toBeInTheDocument();
    });

    it('aligns assistant messages to the left', () => {
      const { container } = render(
        <ChatMessage
          role="assistant"
          content="Test"
          timestamp={mockTimestamp}
        />
      );

      const messageWrapper = container.querySelector('.justify-start');
      expect(messageWrapper).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('handles empty content', () => {
      render(
        <ChatMessage
          role="user"
          content=""
          timestamp={mockTimestamp}
        />
      );

      // Should still render the message container
      expect(screen.getByText('U')).toBeInTheDocument();
    });

    it('handles very long messages', () => {
      const longContent = 'A'.repeat(10000);
      render(
        <ChatMessage
          role="user"
          content={longContent}
          timestamp={mockTimestamp}
        />
      );

      expect(screen.getByText(longContent)).toBeInTheDocument();
    });

    it('handles special characters in content', () => {
      const specialContent = '<script>alert("xss")</script>';
      render(
        <ChatMessage
          role="user"
          content={specialContent}
          timestamp={mockTimestamp}
        />
      );

      // Should render as text, not execute script
      expect(screen.getByText(specialContent)).toBeInTheDocument();
    });

    it('handles markdown links in assistant messages', () => {
      render(
        <ChatMessage
          role="assistant"
          content="Check out [this link](https://example.com)"
          timestamp={mockTimestamp}
        />
      );

      const link = screen.getByRole('link', { name: /this link/ });
      expect(link).toHaveAttribute('href', 'https://example.com');
    });

    it('handles markdown lists in assistant messages', () => {
      const { container } = render(
        <ChatMessage
          role="assistant"
          content="- Item 1\n- Item 2\n- Item 3"
          timestamp={mockTimestamp}
        />
      );

      // Check for list element
      const listElement = container.querySelector('ul');
      expect(listElement).toBeInTheDocument();
      expect(listElement?.textContent).toContain('Item 1');
    });
  });

  describe('Accessibility', () => {
    it('has proper role indicators', () => {
      render(
        <ChatMessage
          role="user"
          content="Test message"
          timestamp={mockTimestamp}
        />
      );

      // User indicator should be present
      expect(screen.getByText('U')).toBeInTheDocument();
    });

    it('maintains proper semantic structure', () => {
      const { container } = render(
        <ChatMessage
          role="assistant"
          content="# Heading\n\nParagraph text"
          timestamp={mockTimestamp}
        />
      );

      // Should have proper heading structure from markdown
      const heading = screen.getByRole('heading');
      expect(heading).toBeInTheDocument();
    });
  });
});
