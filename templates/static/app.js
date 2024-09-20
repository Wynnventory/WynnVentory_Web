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
    toggleContent.addEventListener('show.bs.collapse', function () {
        itemsContainer.classList.add('dtog');
    });

    toggleContent.addEventListener('hide.bs.collapse', function () {
        itemsContainer.classList.remove('dtog');
    });
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
            const { base, identifications, requirements, powder_slots, rarity, item_type, attack_speed, class_req, name } = itemStats;
            let requirementsHTML = '';
            if (item_type === 'weapon') {
                requirementsHTML = `<div>Class Req: ${class_req}<br>Combat Lv. Min: ${requirements.Level}<br>`;
                for (const [key, value] of Object.entries(requirements)) {
                    if (key !== 'Level') {
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

    toggleContainer.addEventListener('click', () => {
        arrow.classList.toggle('collapsed');
        arrow.innerHTML = arrow.classList.contains('collapsed') ? '▲' : '▼';
    });


//items.html Javascript code


//lootpool.html Javascript code

    document.addEventListener('DOMContentLoaded', (event) => {
        // Lootpool reset time
        function getNextResetTime() {
            const now = new Date();
            const nextFriday = new Date();

            nextFriday.setUTCDate(now.getUTCDate() + ((5 - now.getUTCDay() + 7) % 7));
            nextFriday.setUTCHours(18, 0, 0, 0); // 8 PM UTC

            // If today is Friday and past 8 PM UTC, set to next week
            if (now.getUTCDay() === 5 && now.getUTCHours() >= 20) {
                nextFriday.setUTCDate(nextFriday.getUTCDate() + 7);
            }

            return nextFriday;
        }

        function updateCountdown() {
            const now = new Date();
            const nextResetTime = getNextResetTime();
            const timeDiff = nextResetTime - now;

            const days = Math.floor(timeDiff / (1000 * 60 * 60 * 24));
            const hours = Math.floor((timeDiff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((timeDiff % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((timeDiff % (1000 * 60)) / 1000);

            document.getElementById('time').innerHTML = `New items in: ${days}d ${hours}h ${minutes}m ${seconds}s`;

            setTimeout(updateCountdown, 1000);
        }

        updateCountdown();
    });

    function displayItem(event, encodedItemName) {
        const itemName = decodeURIComponent(encodedItemName);
        fetchItemStats(itemName).then(data => {
            if (data) {
                showTooltip(event, data);
            } else {
                console.error('No stats available for this item');
            }
        }).catch(error => {
            console.error('Error fetching item stats:', error);
        });
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

    function showTooltip(event, itemStats) {
        const tooltip = document.getElementById('item-stats-tooltip');
        const { base, identifications, requirements, powder_slots, rarity, item_type, attack_speed, class_req } = itemStats;
        tooltip.classList.remove('Mythic', 'Fabled', 'Legendary', 'Rare', 'Unique');
        tooltip.classList.add(rarity);

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
        `;

        tooltip.style.display = 'block';

        const tooltipRect = tooltip.getBoundingClientRect();
        const viewportHeight = window.innerHeight;
        const viewportWidth = window.innerWidth;

        let top = event.pageY - 100;
        let left = event.pageX + 25;

        if (top + tooltipRect.height > viewportHeight) {
            top = viewportHeight - tooltipRect.height - 10;
        }

        if (left + tooltipRect.width > viewportWidth) {
            left = viewportWidth - tooltipRect.width - 10;
        }

        tooltip.style.top = `${top}px`;
        tooltip.style.left = `${left}px`;

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

//lootpool.html Javascript code
