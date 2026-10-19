import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export function Markdown({ children, className }: { children: string; className?: string }) {
  return (
    <div className={`md ${className ?? ''}`}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </div>
  );
}

export function CodeBlock({ code }: { code: string }) {
  return (
    <pre className="codeblock">
      <code>{code}</code>
    </pre>
  );
}
