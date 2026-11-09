import { describe, expect, it } from "vitest";

import {
  contextualHelpArticle,
  helpArticlesForUser,
  searchHelpArticles,
} from "./helpArticles";
import { modules } from "./modules";

describe("role-aware help registry", () => {
  it("keeps every guide short enough for field use", () => {
    const articles = helpArticlesForUser("operations_manager", "management");
    expect(articles.every((article) => article.steps.length > 0 && article.steps.length <= 5)).toBe(true);
  });

  it("covers every module shown in the management navigation", () => {
    const articles = helpArticlesForUser("operations_manager", "management");
    for (const module of modules) {
      expect(articles.some((article) => article.kind === "module" && article.path === module.path)).toBe(true);
    }
  });

  it("shows employees field instructions without management-only modules", () => {
    const articles = helpArticlesForUser("viewer", "employee");
    expect(articles.some((article) => article.id === "employee-enter-time")).toBe(true);
    expect(articles.some((article) => article.id === "field-complete-flha")).toBe(true);
    expect(articles.some((article) => article.path === "/finance")).toBe(false);
    expect(articles.some((article) => article.id === "management-verbal-quote")).toBe(false);
  });

  it("gives foremen crew guidance without employee-only time guidance", () => {
    const articles = helpArticlesForUser("viewer", "foreman");
    expect(articles.some((article) => article.id === "foreman-crew-time")).toBe(true);
    expect(articles.some((article) => article.id === "foreman-record-production")).toBe(true);
    expect(articles.some((article) => article.id === "employee-enter-time")).toBe(false);
  });

  it("selects the most specific guide for the page the user came from", () => {
    const articles = helpArticlesForUser("viewer", "employee");
    expect(contextualHelpArticle("/employee-portal/receipts", articles)?.id).toBe("employee-submit-receipt");
    expect(contextualHelpArticle("/employee-portal", articles)?.id).toBe("module-employee-portal-workforce");
  });

  it.each([
    ["PO", "field-request-po"],
    ["FLHA", "field-complete-flha"],
    ["receipt reimbursement", "employee-submit-receipt"],
    ["small equipment damage", "field-inspect-equipment"],
  ])("finds common field language: %s", (query, expectedId) => {
    const articles = helpArticlesForUser("viewer", "employee");
    expect(searchHelpArticles(articles, query).some((article) => article.id === expectedId)).toBe(true);
  });
});
