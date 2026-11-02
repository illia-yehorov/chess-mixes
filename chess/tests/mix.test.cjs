"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const template = fs.readFileSync(
    path.join(__dirname, "../templates/mix.html"), "utf8"
);
const script = template.match(/<script>([\s\S]*?)<\/script>/)[1];

function setup(store, weights = { 3: 15, 4: 5 }, themeWeights = { a: 1, b: 1 }) {
    const idMoves = new Map();
    const puzzles = Object.fromEntries(
        Object.keys(themeWeights).map(theme => [
            theme,
            Object.fromEntries(
                Object.keys(weights).map(moveCount => {
                    const ids = Array.from(
                        { length: 100 },
                        (_, index) => theme + "-" + moveCount + "-" + index
                    );
                    ids.forEach(id => idMoves.set(id, Number(moveCount)));
                    return [moveCount, ids];
                })
            )
        ])
    );
    const data = {
        puzzles,
        themes: Object.keys(themeWeights).map((id, i) => ({
            id, number: i + 1, name: id, weight: themeWeights[id]
        })),
        themeWeights,
        moveWeights: weights,
        puzzlesPerClick: 10,
        storageKey: "usedPuzzles:test"
    };
    const opened = [];
    const elements = new Map();
    function createElement(tagName) {
        return {
            tagName,
            children: [],
            hidden: true,
            textContent: "",
            append(...children) { this.children.push(...children); },
            appendChild(child) { this.children.push(child); },
            replaceChildren(...children) { this.children = children; }
        };
    }
    const context = {
        document: {
            title: "Chess Mix Test",
            createElement,
            getElementById(id) {
                if (!elements.has(id)) {
                    elements.set(id, createElement(id));
                }
                return elements.get(id);
            }
        },
        localStorage: {
            getItem: key => store.get(key) ?? null,
            setItem: (key, value) => store.set(key, value),
            removeItem: key => store.delete(key)
        },
        window: {
            open: url => opened.push(url.split("/").pop())
        },
        alert: message => { throw new Error(message); },
        console
    };
    vm.createContext(context);
    vm.runInContext(
        script.replace("{{APP_DATA_JSON}}", JSON.stringify(data)),
        context
    );
    return { context, opened, idMoves, elements };
}

test("15:5 quotas are balanced over two clicks, including a page reload", () => {
    const store = new Map();
    const first = setup(store);
    vm.runInContext("nextPuzzles()", first.context);
    assert.equal(first.opened.length, 10);
    const firstFours = first.opened.filter(id => first.idMoves.get(id) === 4).length;
    assert.ok([2, 3].includes(firstFours));

    const second = setup(store);
    vm.runInContext("nextPuzzles()", second.context);
    assert.equal(second.opened.length, 10);
    const totalFours = firstFours
        + second.opened.filter(id => second.idMoves.get(id) === 4).length;
    assert.equal(totalFours, 5);
    assert.equal(new Set([...first.opened, ...second.opened]).size, 20);
    const persisted = JSON.parse(store.get("usedPuzzles:test:moveBalance"));
    assert.equal(persisted.counts[3], 15);
    assert.equal(persisted.counts[4], 5);
});

test("a single move count gets every slot", () => {
    const page = setup(new Map(), { 4: 5 });
    vm.runInContext("nextPuzzles()", page.context);
    assert.equal(page.opened.length, 10);
    assert.ok(page.opened.every(id => page.idMoves.get(id) === 4));
});

test("zero-weight themes never receive a task", () => {
    const page = setup(new Map(), { 3: 15, 4: 5 }, { a: 1, b: 0 });
    vm.runInContext("nextPuzzles()", page.context);
    assert.equal(page.opened.length, 10);
    assert.ok(page.opened.every(id => id.startsWith("a-")));
});

test("changed weights reset quota state without clearing the used-ID history", () => {
    const store = new Map();
    const first = setup(store);
    vm.runInContext("nextPuzzles()", first.context);
    const next = setup(store, { 3: 1, 4: 1 });
    vm.runInContext("nextPuzzles()", next.context);
    assert.equal(next.opened.filter(id => next.idMoves.get(id) === 4).length, 5);
    assert.equal(new Set([...first.opened, ...next.opened]).size, 20);
});

test("an exhausted used-ID cycle never repeats an ID in one click", () => {
    const store = new Map();
    const usedFours = Array.from(
        { length: 100 },
        (_, index) => ["a-4-" + index, "b-4-" + index]
    ).flat();
    store.set("usedPuzzles:test", JSON.stringify(usedFours));
    const page = setup(store);
    vm.runInContext("nextPuzzles()", page.context);
    assert.equal(page.opened.length, 10);
    assert.equal(new Set(page.opened).size, 10);
});


test("last batch IDs are displayed in tab order with direct puzzle links", () => {
    const store = new Map();
    const page = setup(store);
    vm.runInContext("nextPuzzles()", page.context);

    const section = page.elements.get("last-selection");
    const items = page.elements.get("last-selection-list").children;
    assert.equal(section.hidden, false);
    assert.equal(items.length, page.opened.length);
    page.opened.forEach((id, index) => {
        assert.equal(items[index].children[0], (index + 1) + ". ");
        const link = items[index].children[1];
        assert.equal(link.textContent, "#" + id);
        assert.equal(link.href, "https://lichess.org/training/" + id);
        assert.equal(link.target, "_blank");
    });
    const saved = JSON.parse(store.get("usedPuzzles:test:lastSelection:Chess Mix Test"));
    assert.deepEqual(saved, page.opened);
});

test("last batch stays visible on reload and changes on the next click", () => {
    const store = new Map();
    const first = setup(store);
    vm.runInContext("nextPuzzles()", first.context);

    const reloaded = setup(store);
    const previousLinks = reloaded.elements.get("last-selection-list").children
        .map(item => item.children[1].textContent.slice(1));
    assert.deepEqual(previousLinks, first.opened);

    vm.runInContext("nextPuzzles()", reloaded.context);
    const newLinks = reloaded.elements.get("last-selection-list").children
        .map(item => item.children[1].textContent.slice(1));
    assert.deepEqual(newLinks, reloaded.opened);
    assert.equal(new Set([...previousLinks, ...newLinks]).size, 20);
});
