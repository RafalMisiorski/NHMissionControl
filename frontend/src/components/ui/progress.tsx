import * as React from 'react';
import clsx from 'clsx';

export interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: number;
  indicatorClassName?: string;
}

const Progress = React.forwardRef<HTMLDivElement, ProgressProps>(
  ({ className, value = 0, indicatorClassName, ...props }, ref) => (
    <div
      ref={ref}
      className={clsx(
        'relative h-4 w-full overflow-hidden rounded-full bg-zinc-100',
        className
      )}
      {...props}
    >
      <div
        className={clsx(
          'h-full w-full flex-1 bg-zinc-900 transition-all',
          indicatorClassName
        )}
        style={{ transform: `translateX(-${100 - (value || 0)}%)` }}
      />
    </div>
  )
);
Progress.displayName = 'Progress';

export { Progress };
