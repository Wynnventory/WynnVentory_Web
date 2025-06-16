//base.html Javascript code

document.addEventListener('DOMContentLoaded', (event) => {
    const htmlElement = document.documentElement;
    const switchElement = document.getElementById('darkModeSwitch');

    // Set the default theme to dark if no setting is found in local storage
    const currentTheme = localStorage.getItem('bsTheme') || 'dark';
    htmlElement.setAttribute('data-bs-theme', currentTheme);
    switchElement.checked = currentTheme === 'dark';

    switchElement.addEventListener('change', function () {
        if (this.checked) {
            htmlElement.setAttribute('data-bs-theme', 'dark');
            localStorage.setItem('bsTheme', 'dark');
        } else {
            htmlElement.setAttribute('data-bs-theme', 'light');
            localStorage.setItem('bsTheme', 'light');
        }
    });
});

//base.html Javascript code


//items.html Javascript code

const toggleContent = document.getElementById('toggleContent');
const itemsContainer = document.getElementById('items-container');

// Add event listeners for Bootstrap collapse events
if (toggleContent) {
    toggleContent.addEventListener('show.bs.collapse', function () {
        itemsContainer.classList.add('dtog');
    });

    toggleContent.addEventListener('hide.bs.collapse', function () {
        itemsContainer.classList.remove('dtog');
    });
}

function removeClass() {
    const itemsContainer = document.getElementById('items-container');
    itemsContainer.classList.remove('dtog');

}

const toggleContainer = document.querySelector('.toggle-container');
const arrow = document.querySelector('.arrow');
const selectedFilters = [];

// Toggle filter button and update selected filters
function toggleFilter(button, filterTypes) {
    const filters = filterTypes.split(',').map(filter => filter.trim());
    const isActive = button.classList.toggle('active');

    filters.forEach(filter => {
        if (isActive) {
            if (!selectedFilters.includes(filter)) {
                selectedFilters.push(filter);
            }
        } else {
            const index = selectedFilters.indexOf(filter);
            if (index > -1) {
                selectedFilters.splice(index, 1);
            }
        }
    });
}

// Submit search query to the server
function submitSearch() {
    const query = document.getElementById('search-query').value;
    const payload = {
        query: query,
        type: selectedFilters.length > 0 ? selectedFilters : ['weapon', 'helmet', 'chestplate', 'leggings', 'boots', 'necklace', 'bracelet', 'ring'],
        tier: [],
        attackSpeed: [],
        levelRange: [0, 110],
        professions: [],
        identifications: [],
        majorIds: []
    };
    fetchItems(payload);
}

// Fetch items from the server
async function fetchItems(payload) {
    console.log(payload);
    const response = await fetch('/api/items', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
    });
    if (response.ok) {
        const data = await response.json();
        displayItems(data.items);
    } else {
        console.error('Failed to fetch items');
    }
}

// Display items inside the items-container
function displayItems(items) {
    const container = document.getElementById('items-container').querySelector('.row');
    container.innerHTML = ''; // Clear previous items

    items.forEach(itemStats => {
        const {
            base,
            identifications,
            requirements,
            powder_slots,
            rarity,
            item_type,
            attack_speed,
            class_req,
            name
        } = itemStats;
        let requirementsHTML = '';
        if (item_type === 'weapon') {
            requirementsHTML = `<div>Class Req: ${class_req}<br>Combat Lv. Min: ${requirements.Level}<br>`;
            for (const [key, value] of Object.entries(requirements)) {
                if (key !== 'Level' && key !== 'Classrequirement') {
                    requirementsHTML += `${key} Min: ${value}<br>`;
                }
            }
            requirementsHTML += '</div>';
        } else {
            requirementsHTML = `<div>Combat Lv. Min: ${requirements.Level}<br>`;
            for (const [key, value] of Object.entries(requirements)) {
                if (key === 'class_req' && key !== 'Classrequirement') {
                    requirementsHTML += `Class Req: ${value}<br>`;
                } else if (key !== 'Level') {
                    requirementsHTML += `${key} Min: ${value}<br>`;
                }
            }
            requirementsHTML += '</div>';
        }

        let rawIdentificationsHTML = '';
        let otherIdentificationsHTML = '';

        for (const [key, value] of Object.entries(identifications)) {
            const minValue = value.min_value !== undefined ? value.min_value : value;
            const maxValue = value.max_value !== undefined ? value.max_value_readable : value;
            const rawValue = value.raw !== undefined ? value.raw_readable : value;
            const colorClass = value.raw >= 0 ? 'positive' : 'negative';
            const toColorClass = value.raw >= 0 ? 'positive-to' : 'negative-to';

            const identificationHTML = minValue !== null && maxValue !== null
                ? `
                    <span class="${colorClass}">${minValue}</span>
                    <span class="${toColorClass}"> to </span>
                    <span class="${colorClass}">${maxValue}</span>
                    <span class="stat-name"> ${value.readable_name}</span><br>
                `
                : `
                    <span class="${colorClass}">${rawValue}</span>
                    <span class="stat-name"> ${value.readable_name}</span><br>
                `;

            if (key.startsWith('raw')) {
                rawIdentificationsHTML += identificationHTML;
            } else {
                otherIdentificationsHTML += identificationHTML;
            }
        }

        const itemCardHTML = `
            <div class="col item-stats-tooltip ${rarity} items-handle">
                <div class="item-card">
                    <div class="item-header">
                        <h5 class="${rarity}">${name}</h5>
                        ${item_type === 'weapon' ? `<span class="attack-speed item-text">${attack_speed} Attack Speed</span>` : ''}
                    </div>
                    <div class="item-infobox defence item-text">
                        ${item_type === 'weapon' ? `
                            ${base.damage ? `<span class="item-text neutral"><span>Neutral</span> Damage: </span><span class="${base.damage >= 0 ? 'positive' : 'negative'}">${base.damage.min}-${base.damage.max}</span><br>` : ''}
                            ${base.air_damage ? `<span class="item-text air"><span>Air</span> Damage: </span><span class="${base.air_damage >= 0 ? 'positive' : 'negative'}">${base.air_damage.min}-${base.air_damage.max}</span><br>` : ''}
                            ${base.earth_damage ? `<span class="item-text earth"><span>Earth</span> Damage: </span><span class="${base.earth_damage >= 0 ? 'positive' : 'negative'}">${base.earth_damage.min}-${base.earth_damage.max}</span><br>` : ''}
                            ${base.fire_damage ? `<span class="item-text fire"><span>Fire</span> Damage: </span><span class="${base.fire_damage >= 0 ? 'positive' : 'negative'}">${base.fire_damage.min}-${base.fire_damage.max}</span><br>` : ''}
                            ${base.thunder_damage ? `<span class="item-text thunder"><span>Thunder</span> Damage: </span><span class="${base.thunder_damage >= 0 ? 'positive' : 'negative'}">${base.thunder_damage.min}-${base.thunder_damage.max}</span><br>` : ''}
                            ${base.water_damage ? `<span class="item-text water"><span>Water</span> Damage: </span><span class="${base.water_damage >= 0 ? 'positive' : 'negative'}">${base.water_damage.min}-${base.water_damage.max}</span><br>` : ''}
                            <span class="item-text-dark">Average DPS: <span class="item-text">${base.average_dps}</span></span>
                        ` : `
                            ${base.health ? `<span class="item-health">Health: <span class="${base.health >= 0 ? 'positive' : 'negative'}">${base.health} </span></span><br>` : ''}
                            ${base.fire_defence ? `<span class="item-text fire"><span>Fire</span> Defence: </span><span class="item-text ${base.fire_defence >= 0 ? 'positive' : 'negative'}">${base.fire_defence}</span><br>` : ''}
                            ${base.water_defence ? `<span class="item-text water"><span>Water</span> Defence: </span><span class="item-text ${base.water_defence >= 0 ? 'positive' : 'negative'}">${base.water_defence}</span><br>` : ''}
                            ${base.air_defence ? `<span class="item-text air"><span>Air</span> Defence: </span><span class="item-text ${base.air_defence >= 0 ? 'positive' : 'negative'}">${base.air_defence}</span><br>` : ''}
                            ${base.thunder_defence ? `<span class="item-text thunder"><span>Thunder</span> Defence: </span><span class="item-text ${base.thunder_defence >= 0 ? 'positive' : 'negative'}">${base.thunder_defence}</span><br>` : ''}
                            ${base.earth_defence ? `<span class="item-text earth"><span>Earth</span> Defence: </span><span class="item-text ${base.earth_defence >= 0 ? 'positive' : 'negative'}">${base.earth_defence}</span><br>` : ''}
                        `}
                    </div>
                    <div class="item-infobox item-text">
                        ${requirementsHTML}
                    </div>
                    <div class="item-infobox item-text">
                        ${rawIdentificationsHTML}
                    </div>
                    <div class="item-infobox item-text">
                        ${otherIdentificationsHTML}
                    </div>
                    ${item_type === 'accessory' ? `
                    <div class="item-infobox ${rarity}">
                        ${rarity} Item
                    </div>
                    ` : `
                    <div class="item-infobox item-text">
                        [0/${powder_slots}] Powder Slots
                    </div>
                    <div class="${rarity}">
                        ${rarity} Item
                    </div>
                    `}
                </div>
            </div>
        `;

        container.insertAdjacentHTML('beforeend', itemCardHTML);
    });
}

if (document.getElementById('collapse-button')) {
    document.getElementById('collapse-button').addEventListener('click', function () {
        const filterContainer = document.getElementById('filter-sidebar');
        filterContainer.classList.toggle('collapsed');
        if (filterContainer.classList.contains('collapsed')) {
            this.innerHTML = '<';
        } else {
            this.innerHTML = '>';
        }
        document.getElementById('items-container').classList.toggle('expanded');
    });
}

if (toggleContainer) {
    toggleContainer.addEventListener('click', () => {
        arrow.classList.toggle('collapsed');
        arrow.innerHTML = arrow.classList.contains('collapsed') ? '▲' : '▼';
    });
}


//items.html Javascript code


//lootrun_lootpool.html Javascript code
document.addEventListener('DOMContentLoaded', () => {
    const lootEl = document.getElementById('lootTime')
    const raidEl = document.getElementById('raidTime')

    // Returns the next Friday at given UTC hour (18 for loot, 17 for raid)
    function getNextFridayAt(hourUTC) {
        const now = new Date()
        const next = new Date()
        // days until Friday (5)
        next.setUTCDate(
            now.getUTCDate() + ((5 - now.getUTCDay() + 7) % 7)
        )
        next.setUTCHours(hourUTC, 0, 0, 0)

        // if it’s already past that hour on Friday, bump a week
        if (now.getUTCDay() === 5 && now.getUTCHours() >= hourUTC) {
            next.setUTCDate(next.getUTCDate() + 7)
        }
        return next
    }

    // Generic countdown starter: takes a “getNext” fn and an element to update
    function startCountdown(getNextFn, el) {
        function tick() {
            const now = new Date()
            let target = getNextFn()
            let diff = target - now

            // if negative, roll over to next week
            if (diff <= 0) {
                target.setUTCDate(target.getUTCDate() + 7)
                diff = target - now
            }

            const days = Math.floor(diff / (1000 * 60 * 60 * 24))
            const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
            const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
            const seconds = Math.floor((diff % (1000 * 60)) / 1000)

            el.innerHTML = `New items in: ${days}d ${hours}h ${minutes}m ${seconds}s`
            setTimeout(tick, 1000)
        }

        tick()
    }

    // Only start the one if its element is actually on the page
    if (lootEl) startCountdown(() => getNextFridayAt(18), lootEl)
    if (raidEl) startCountdown(() => getNextFridayAt(17), raidEl)
})

function displayItem(e, encodedItemName) {
    e.preventDefault();
    // allow both click and touchstart
    const touch = (e.touches && e.touches[0]);
    const clickX = touch ? touch.clientX : e.clientX;
    const clickY = touch ? touch.clientY : e.clientY;

    const name = decodeURIComponent(encodedItemName);
    fetchItemStats(name)
        .then(data => data ? showTooltip(e, data, clickX, clickY) : console.error('No stats'))
        .catch(err => console.error('Fetch error', err));
}

async function fetchItemStats(itemName) {
    const response = await fetch(`/api/item/${encodeURIComponent(itemName)}`);
    if (response.ok) {
        const data = await response.json();
        return data;
    } else {
        console.error('Failed to fetch item stats');
        return null;
    }
}

function displayAspect(event, encodedAspectClass, encodedItemName) {
    const aspectClass = decodeURIComponent(encodedAspectClass).replace('Aspect', '').toLowerCase();
    const aspectName = decodeURIComponent(encodedItemName);

    const touch = (event.touches && event.touches[0]);
    const clickX = touch ? touch.clientX : event.clientX;
    const clickY = touch ? touch.clientY : event.clientY;

    fetchAspectStats(aspectClass, aspectName).then(data => {
        if (data) {
            showTooltipAspect(event, data, clickX, clickY);
        } else {
            console.error('No stats available for this item');
        }
    }).catch(error => {
        console.error('Error fetching item stats:', error);
    });
}

async function fetchAspectStats(className, aspectName) {
    const response = await fetch(`/api/aspect/${encodeURIComponent(className)}/${encodeURIComponent(aspectName)}`);
    if (response.ok) {
        const data = await response.json();
        return data;
    } else {
        console.error('Failed to fetch item stats');
        return null;
    }
}

function showTooltipAspect(e, aspectStats, clickX, clickY) {
    const tooltip = document.getElementById('item-stats-tooltip');
    const {rarity, requiredClass, tiers, name} = aspectStats;
    tooltip.className = 'item-stats-tooltip ' + rarity;

    // Tier
    let tierHTML = '';
    tierHTML = `<div>Tier I 
                <span style="color:darkgray;">>>>>>>>>></span>
                <span class="${rarity}"> Tier II </span>[0/${tiers[2].threshold - 1}]<br></div>`;

    // Description
    let descriptionHTML = '';
    descriptionHTML = `<div>${tiers[1].description}<br></div>`;

    // Requirements
    let requirementsHTML = '';
    requirementsHTML = `<div>Class Req: <span style="color: white;">${requiredClass.charAt(0).toUpperCase() + requiredClass.slice(1)}</span><br></div>`;

    // build your tiers & description HTML…
    tooltip.innerHTML = `
        <div class="item-header">
            <h5 class="${rarity}">${aspectStats.name}</h5>
        </div>
        <div class="item-infobox item-tiertext item-text">
            ${tierHTML}
        </div>
        <div class="item-infobox item-text">
            ${descriptionHTML}
        </div>
        <div class="item-infobox item-text">
            ${requirementsHTML}
        </div>
    `;

    tooltip.style.display = 'block';
    positionTooltip(tooltip, clickX, clickY);
    document.addEventListener('click', hideTooltipOnClickOutside);
}

function showTooltip(e, itemStats, clickX, clickY) {
    const tooltip = document.getElementById('item-stats-tooltip');
    const {base, identifications, requirements, powder_slots, rarity, item_type, attack_speed, class_req} = itemStats;

    // reset & set rarity class
    tooltip.className = 'item-stats-tooltip ' + rarity;


    // Requirements
    let requirementsHTML = '';
    if (item_type === 'weapon') {
        requirementsHTML = `<div>Class Req: ${class_req}<br>Combat Lv. Min: ${requirements.Level}<br>`;
        for (const [key, value] of Object.entries(requirements)) {
            if (key !== 'Level' && key !== 'Classrequirement') {
                requirementsHTML += `${key} Min: ${value}<br>`;
            }
        }
        requirementsHTML += '</div>';
    } else {
        requirementsHTML = `<div>Combat Lv. Min: ${requirements.Level}<br>`;
        for (const [key, value] of Object.entries(requirements)) {
            if (key === 'class_req') {
                requirementsHTML += `Class Req: ${value}<br>`;
            } else if (key !== 'Level') {
                requirementsHTML += `${key} Min: ${value}<br>`;
            }
        }
        requirementsHTML += '</div>';
    }

    // Identifications
    let rawIdentificationsHTML = '';
    let otherIdentificationsHTML = '';

    for (const [key, value] of Object.entries(identifications)) {
        const minValue = value.min_value !== undefined ? value.min_value : value;
        const maxValue = value.max_value !== undefined ? value.max_value_readable : value;
        const rawValue = value.raw !== undefined ? value.raw_readable : value;
        const colorClass = value.raw >= 0 ? 'positive' : 'negative';
        const toColorClass = value.raw >= 0 ? 'positive-to' : 'negative-to';

        const identificationHTML = minValue !== null && maxValue !== null
            ? `
            <span class="${colorClass}">${minValue}</span>
            <span class="${toColorClass}"> to </span>
            <span class="${colorClass}">${maxValue}</span>
            <span class="stat-name"> ${value.readable_name}</span><br>
        `
            : `
            <span class="${colorClass}">${rawValue}</span>
            <span class="stat-name"> ${value.readable_name}</span><br>
        `;

        if (key.startsWith('raw')) {
            rawIdentificationsHTML += identificationHTML;
        } else {
            otherIdentificationsHTML += identificationHTML;
        }
    }

    // Build item tooltip
    tooltip.innerHTML = `
            <div class="item-header">
                <h5 class="${rarity}">${itemStats.name}</h5>
                ${item_type === 'weapon' ? `<span class="attack-speed item-text">${attack_speed} Attack Speed</span>` : ''}
            </div>
            <div class="item-infobox defence item-text">
                ${item_type === 'weapon' ? `
                    ${base.damage ? `<span class="item-text neutral"><span>Neutral</span> Damage: </span><span class="${base.damage >= 0 ? 'positive' : 'negative'}">${base.base_damage.min}-${base.base_damage.max}</span><br>` : ''}
                    ${base.air_damage ? `<span class="item-text air"><span>Air</span> Damage: </span><span class="${base.air_damage >= 0 ? 'positive' : 'negative'}">${base.air_damage.min}-${base.air_damage.max}</span><br>` : ''}
                    ${base.earth_damage ? `<span class="item-text earth"><span>Earth</span> Damage: </span><span class="${base.earth_damage >= 0 ? 'positive' : 'negative'}">${base.earth_damage.min}-${base.earth_damage.max}</span><br>` : ''}
                    ${base.fire_damage ? `<span class="item-text fire"><span>Fire</span> Damage: </span><span class="${base.fire_damage >= 0 ? 'positive' : 'negative'}">${base.fire_damage.min}-${base.fire_damage.max}</span><br>` : ''}
                    ${base.thunder_damage ? `<span class="item-text thunder"><span>Thunder</span> Damage: </span><span class="${base.thunder_damage >= 0 ? 'positive' : 'negative'}">${base.thunder_damage.min}-${base.thunder_damage.max}</span><br>` : ''}
                    ${base.water_damage ? `<span class="item-text water"><span>Water</span> Damage: </span><span class="${base.water_damage >= 0 ? 'positive' : 'negative'}">${base.water_damage.min}-${base.water_damage.max}</span><br>` : ''}
                    <span class="item-text-dark">Average DPS: <span class="item-text">${base.average_dps}</span></span>
                ` : `
                    ${base.health ? `<span class="item-health">Health: <span class="${base.health >= 0 ? 'positive' : 'negative'}">${base.health} </span></span><br>` : ''}
                    ${base.fire_defence ? `<span class="item-text fire"><span>Fire</span> Defence: </span><span class="item-text ${base.fire_defence >= 0 ? 'positive' : 'negative'}">${base.fire_defence}</span><br>` : ''}
                    ${base.water_defence ? `<span class="item-text water"><span>Water</span> Defence: </span><span class="item-text ${base.water_defence >= 0 ? 'positive' : 'negative'}">${base.water_defence}</span><br>` : ''}
                    ${base.air_defence ? `<span class="item-text air"><span>Air</span> Defence: </span><span class="item-text ${base.air_defence >= 0 ? 'positive' : 'negative'}">${base.air_defence}</span><br>` : ''}
                    ${base.thunder_defence ? `<span class="item-text thunder"><span>Thunder</span> Defence: </span><span class="item-text ${base.thunder_defence >= 0 ? 'positive' : 'negative'}">${base.thunder_defence}</span><br>` : ''}
                    ${base.earth_defence ? `<span class="item-text earth"><span>Earth</span> Defence: </span><span class="item-text ${base.earth_defence >= 0 ? 'positive' : 'negative'}">${base.earth_defence}</span><br>` : ''}
                `}
            </div>
            <div class="item-infobox item-text">
                ${requirementsHTML}
            </div>
            <div class="item-infobox item-text">
                ${rawIdentificationsHTML}
            </div>
            <div class="item-infobox item-text">
                ${otherIdentificationsHTML}
            </div>
            ${item_type === 'accessory' || item_type === 'tome' ? `
            <div class="item-infobox ${rarity}">
                ${item_type === 'tome' ? `${rarity} Raid Reward` : `${rarity} Item`}
            </div>
            ` : `
            <div class="item-infobox item-text">
                [0/${powder_slots}] Powder Slots
            </div>
            <div class="${rarity}">
                ${rarity} Item
            </div>
            `}
        `;

    tooltip.style.display = 'block';
    positionTooltip(tooltip, clickX, clickY);
    document.addEventListener('click', hideTooltipOnClickOutside);
}

function hideTooltip() {
    const tooltip = document.getElementById('item-stats-tooltip');
    tooltip.style.display = 'none';
    document.removeEventListener('click', hideTooltipOnClickOutside);
}

function hideTooltipOnClickOutside(event) {
    const tooltip = document.getElementById('item-stats-tooltip');
    if (!tooltip.contains(event.target)) {
        hideTooltip();
    }
}

// helper to keep both tooltips in sync
function positionTooltip(tooltip, clickX, clickY) {
    const rect = tooltip.getBoundingClientRect();
    const vw = window.innerWidth, vh = window.innerHeight;
    let top = clickY - 100;
    let left = clickX + 25;

    let gap = 10;
    // clamp inside viewport
    if (top + rect.height > vh) top = vh - rect.height - gap;
    if (left + rect.width > vw) left = vw - rect.width - gap;
    if (top < gap) top = gap;
    if (left < gap) left = gap;

    tooltip.style.top = top + 'px';
    tooltip.style.left = left + 'px';
}

//lootrun_lootpool.html Javascript code
