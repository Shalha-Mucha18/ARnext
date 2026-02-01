import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import type { Components } from 'react-markdown';

interface MessageContentProps {
    content: string;
    role: 'user' | 'assistant';
}

export default function MessageContent({ content, role }: MessageContentProps) {
    // User messages render as plain text
    if (role === 'user') {
        return <>{content}</>;
    }

    // Custom components for markdown rendering
    const components: Components = {
        // Custom table styling
        table: ({ node: _node, ...props }) => (
            <div className="markdown-table-wrapper">
                <table className="markdown-table" {...props} />
            </div>
        ),
        // Custom code block styling
        code: ({ node: _node, className, children, ...props }) => {
            const isInline = !className;
            return isInline ? (
                <code className="markdown-inline-code" {...props}>
                    {children}
                </code>
            ) : (
                <code className={`markdown-code-block ${className || ''}`} {...props}>
                    {children}
                </code>
            );
        },
        // Custom heading styling
        h1: ({ node: _node, ...props }) => <h1 className="markdown-h1" {...props} />,
        h2: ({ node: _node, ...props }) => <h2 className="markdown-h2" {...props} />,
        h3: ({ node: _node, ...props }) => <h3 className="markdown-h3" {...props} />,
        h4: ({ node: _node, ...props }) => <h4 className="markdown-h4" {...props} />,
        // Custom list styling
        ul: ({ node: _node, ...props }) => <ul className="markdown-ul" {...props} />,
        ol: ({ node: _node, ...props }) => <ol className="markdown-ol" {...props} />,
        li: ({ node: _node, ...props }) => <li className="markdown-li" {...props} />,
        // Custom paragraph styling
        p: ({ node: _node, ...props }) => <p className="markdown-p" {...props} />,
        // Custom emphasis styling
        strong: ({ node: _node, ...props }) => <strong className="markdown-strong" {...props} />,
        em: ({ node: _node, ...props }) => <em className="markdown-em" {...props} />,
        // Custom horizontal rule
        hr: ({ node: _node, ...props }) => <hr className="markdown-hr" {...props} />,
    };

    // Assistant messages render as markdown
    return (
        <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeHighlight]}
            components={components}
        >
            {content}
        </ReactMarkdown>
    );
}
