import type { ReactNode } from "react";

import { formatKrw } from "./model";
import type { SplitStep } from "./types";

export function PanelTitle({ icon, title }: { icon: ReactNode; title: string }) {
  return (
    <h2 className="panel-title">
      {icon}
      {title}
    </h2>
  );
}

export function ListBlock({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="list-block">
      <h3>{title}</h3>
      <ul>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

export function RuleList({ title, items }: { title: string; items: SplitStep[] }) {
  return (
    <div className="rule-list">
      <h3>{title}</h3>
      {items.map((item) => (
        <div key={`${title}-${item.step}`}>
          <strong>{item.step}</strong>
          <small>
            {item.trigger} · {item.ratio_of_target}% · {formatKrw(item.amount)}
          </small>
        </div>
      ))}
    </div>
  );
}
